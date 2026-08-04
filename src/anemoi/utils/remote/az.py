# (C) Copyright 2024-2026 Anemoi contributors.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Management of objects in Azure Blob Storage.

Provides functions to upload, download, list, and delete files and folders, including hierarchical namespace (Azure Data
Lake Storage Gen 2).

Only `abfs://` scheme URLs are accepted in one of two shapes, including **optional** query strings for SAS tokens (e.g.
suffixed `?sv=...`):

- `abfs://<container>/<path>`: account name comes from settings or environment variables
- `abfs://<container>@<account>.dfs.core.windows.net/<path>?`: account name in the URL (`.blob.core.windows.net` also
accepted)

Credentials can be supplied via `~/.config/anemoi/settings.toml` (or `settings.secrets.toml`) under the `object-storage`
section:

```toml
    [object-storage]
    endpoint_url = "..."  # for Azure, only needed for sovereign clouds / Azurite
    account_name = "..."  # storage account name
    account_key = "..."  # storage account key
    sas_token = "?sv=..."  # SAS token instead of an account key
    skip_signature = true  # for public / anonymous containers

    # container-keyed overrides, if source and destination are in different accounts or have different credentials
    ["object-storage.training-data"]
    account_name = "..."
    sas_token = "?sv=..."
```

Alternatively, `obstore` attempts to read standard Azure environment variables directly if no credentials are configured
as above. For a list of supported environment variables, see
[`obstore` documentation](https://developmentseed.org/obstore/latest/api/store/azure/#obstore.store.AzureConfig).
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import overload

import obstore
import tqdm  # type: ignore[import-untyped]

from ..humanize import bytes_to_human
from ..settings import SETTINGS
from ..settings_schema.object_storage import AZURE_CLIENT_FIELDS
from ..settings_schema.object_storage import ObjectStorageBucketConfig
from . import BaseDownload
from . import BaseUpload
from . import Loader
from . import transfer

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Sequence

    # obstore.ObjectMeta not importable at runtime, must be within TYPE_CHECKING
    from obstore import ObjectMeta

LOG = logging.getLogger(__name__)

# Avoids creating a new connection pool on every Azure read during training.
CLIENT_CACHE: dict[str, obstore.store.ObjectStore] = {}
CLIENT_LOCK = threading.Lock()

_ABFS_SCHEME = "abfs://"
_ABFS_HOST_RE = re.compile(
    r"^(?P<container>[^@/]+)@(?P<account>[^./]+)\.(?:blob|dfs)\.[^/]+$",
    re.IGNORECASE,
)


def _assert_azure_url(url: str) -> None:
    """Assert that a URL is a supported Azure Blob Storage URL.

    Parameters
    ----------
    url : str
        Candidate URL.

    Raises
    ------
    ValueError
        If the URL does not begin with abfs://.

    """
    if not url.lower().startswith(_ABFS_SCHEME):
        msg = f"Invalid Azure URL: {url} (expected '{_ABFS_SCHEME}')"
        raise ValueError(msg)


class AzureObject:
    """Parsed representation of an Azure Blob Storage URL."""

    def __init__(self, url: str) -> None:
        """Parse an Azure Blob Storage URL into container, account, path and optional SAS query.

        Parameters
        ----------
        url : str
            Azure Blob Storage URL beginning with abfs://. Both abfs://<container>/<path> and
            abfs://<container>@<account>.<blob|dfs>.core.windows.net/<path> forms are accepted, with an optional ?<sas>
            query suffix.

        Raises
        ------
        ValueError
            If the URL does not begin with abfs://, or if the container segment is empty.

        """
        self.url = url
        base, _, query = url.partition("?")
        self.query = query  # may contain SAS token
        _assert_azure_url(base)
        rest = base[len(_ABFS_SCHEME) :]
        host_part, _, path = rest.partition("/")

        host_match = _ABFS_HOST_RE.match(host_part)
        if host_match:
            self.account = host_match.group("account")
            self.container = host_match.group("container")
        else:
            self.account = None
            self.container = host_part
        self.path = path

        if not self.container:
            msg = f"Missing container in Azure URL: {url}"
            raise ValueError(msg)

        self.dirname = f"{_ABFS_SCHEME}{self.container}"
        # distinguish same-container-different-account for CLIENT_CACHE
        self.cache_key = f"{self.account or '_'}::{self.container}"


def _azure_object(url_or_object: str | AzureObject) -> AzureObject:
    """Coerce a URL or existing AzureObject into an AzureObject.

    Parameters
    ----------
    url_or_object : str | AzureObject
        Azure Blob Storage URL or a pre-parsed AzureObject.

    Returns
    -------
    AzureObject
        Parsed representation of the given URL, or the input unchanged if already parsed.

    Raises
    ------
    TypeError
        If url_or_object is neither a string nor an AzureObject.

    """
    if isinstance(url_or_object, AzureObject):
        return url_or_object
    if isinstance(url_or_object, str):
        return AzureObject(url_or_object)
    msg = f"Invalid type for Azure object: {type(url_or_object)}"
    raise TypeError(msg)


def _azure_options(obj: str | AzureObject) -> ObjectStorageBucketConfig:
    """Resolve credentials and endpoint for the container referenced by obj.

    Container-keyed overrides under [object-storage.<pattern>] in settings take precedence over the top-level
    [object-storage] block, the pattern is matched against the container name using fnmatch.

    Parameters
    ----------
    obj : str | AzureObject
        Azure Blob Storage URL or a pre-parsed AzureObject.

    Returns
    -------
    ObjectStorageBucketConfig
        Resolved credentials and endpoint for the container.

    Raises
    ------
    ValueError
        If more than one container-keyed override matches obj.container.

    """
    obj = _azure_object(obj)
    object_storage_cfg = SETTINGS.object_storage
    # per-container overrides in __pydantic_extra__, fixed model fields are the globals
    container_overrides = object_storage_cfg.__pydantic_extra__ or {}

    candidate: ObjectStorageBucketConfig | None = None
    candidate_key: str | None = None
    for key in container_overrides:
        if fnmatch.fnmatch(obj.container, key):
            if candidate is not None:
                msg = f"Multiple object storage configurations match {obj.container}: {candidate_key} and {key}"
                raise ValueError(msg)
            candidate = container_overrides[key]
            candidate_key = key

    if candidate:
        config = candidate.model_dump(by_alias=False, exclude_none=True)
    else:
        LOG.debug(
            "No specific object storage configuration found for container %s, using global settings",
            obj.container,
        )
        config = object_storage_cfg.model_dump(by_alias=False, exclude_none=True, include=set(AZURE_CLIENT_FIELDS))

    resolved_object_config = ObjectStorageBucketConfig(**config)
    LOG.info("Using Azure options: %s", resolved_object_config)
    return resolved_object_config


def azure_client(obj: str | AzureObject) -> obstore.store.ObjectStore:
    """Return a cached obstore client for the container referenced by obj.

    The client is keyed by account and container so that requests to different accounts sharing a container name do not
    collide in the cache. Credential precedence, highest to lowest:

    - SAS token in the URL query
    - SAS token in settings
    - Account key in settings
    - Anonymous access (skip_signature).

    If none are set, obstore falls back to the standard AZURE_STORAGE_* environment variables.

    Parameters
    ----------
    obj : str | AzureObject
        Azure Blob Storage URL or a pre-parsed AzureObject.

    Returns
    -------
    obstore.store.ObjectStore
        Ready-to-use client for the account and container referenced by obj.

    """
    obj = _azure_object(obj)

    with CLIENT_LOCK:
        if obj.cache_key in CLIENT_CACHE:
            return CLIENT_CACHE[obj.cache_key]

        options = _azure_options(obj)
        LOG.debug("Using Azure options: %s", options)

        kwargs: dict[str, Any] = {}

        # account name from URL first, then settings
        if obj.account is not None:
            kwargs["account_name"] = obj.account
        elif options.account_name is not None:
            kwargs["account_name"] = options.account_name.get_secret_value()
        # if still unset, obstore attempts AZURE_STORAGE_ACCOUNT_NAME env var

        # endpoint override (sovereign / govt clouds, Azurite, etc.)
        if options.endpoint_url is not None:
            kwargs["endpoint"] = options.endpoint_url

        # credential precedence: SAS in URL > SAS in settings > account key > anonymous
        # if unset, obstore attempts AZURE_STORAGE_* env vars
        if obj.query:
            kwargs["sas_key"] = obj.query
        elif options.sas_token is not None:
            kwargs["sas_key"] = options.sas_token.get_secret_value()
        elif options.account_key is not None:
            kwargs["account_key"] = options.account_key.get_secret_value()
        elif options.skip_signature:
            kwargs["skip_signature"] = True

        CLIENT_CACHE[obj.cache_key] = obstore.store.from_url(obj.dirname, **kwargs)
        return CLIENT_CACHE[obj.cache_key]


@overload
def _list_objects(target: str | AzureObject, *, batch: Literal[True]) -> Iterable[Sequence[ObjectMeta]]: ...


@overload
def _list_objects(target: str | AzureObject, *, batch: Literal[False] = False) -> Iterable[ObjectMeta]: ...


def _list_objects(
    target: str | AzureObject,
    *,
    batch: bool = False,
) -> Iterable[Sequence[ObjectMeta]] | Iterable[ObjectMeta]:
    """List blobs under the URL prefix.

    Parameters
    ----------
    target : str | AzureObject
        Azure Blob Storage URL or a pre-parsed AzureObject used as a prefix. Only blobs whose paths begin with the URL's
        path segment are yielded.
    batch : bool, default = False
        If True, yield one page of blob metadata at a time as returned by obstore, if False, yield one blob at a time.

    Yields
    ------
    Sequence[ObjectMeta] | ObjectMeta
        One blob (batch=False) or one page of blobs (batch=True) per iteration.

    """
    obj = _azure_object(target)
    client = azure_client(obj)
    path = obj.path.strip("/")
    prefix = f"{path}/" if path else ""
    for files in obstore.list(client, prefix, chunk_size=1024):
        if batch:
            yield files
        else:
            yield from files


def list_folder(folder: str) -> Iterable[ObjectMeta]:
    """List blobs under the URL prefix.

    Parameters
    ----------
    folder : str
        Azure Blob Storage URL used as a prefix.

    Returns
    -------
    Iterable[ObjectMeta]
        One item per blob under the prefix.

    """
    return _list_objects(folder)


def delete_folder(target: str) -> None:
    """Delete all blobs under the URL prefix.

    Parameters
    ----------
    target : str
        Azure Blob Storage URL used as a prefix.

    """
    obj = _azure_object(target)
    client = azure_client(obj)
    total = 0
    for batch in _list_objects(obj, batch=True):
        paths = [o["path"] for o in batch]
        LOG.info("Deleting %s objects from %s", len(batch), target)
        obstore.delete(client, paths)
        total += len(batch)
        LOG.info("Deleted %s objects (total=%s)", len(batch), total)


def delete_file(target: str) -> None:
    """Delete a single blob.

    If no blob exists at the URL, a warning is logged and no error is raised.

    Parameters
    ----------
    target : str
        Azure Blob Storage URL for the blob to delete.

    """
    obj = _azure_object(target)
    client = azure_client(obj)
    if not object_exists(obj):
        LOG.warning("%s does not exist. Did you mean to delete a folder? Add a trailing '/'", target)
        return
    LOG.info("Deleting %s", target)
    obstore.delete(client, obj.path)
    LOG.info("%s is deleted", target)


def delete(target: str) -> None:
    """Delete a single blob or all blobs under a prefix.

    Dispatches to delete_folder if target ends with '/', otherwise delete_file.

    Parameters
    ----------
    target : str
        Azure Blob Storage URL. Treated as a prefix if it ends with '/', otherwise as a single blob.

    """
    if target.endswith("/"):
        delete_folder(target)
    else:
        delete_file(target)


def object_info(target: str | AzureObject) -> ObjectMeta:
    """Fetch metadata for a single blob.

    Parameters
    ----------
    target : str | AzureObject
        Azure Blob Storage URL or a pre-parsed AzureObject.

    Returns
    -------
    ObjectMeta
        Metadata for the blob, including size, path, and last-modified time.

    Raises
    ------
    FileNotFoundError
        If no blob exists at the URL.

    """
    obj = _azure_object(target)
    client = azure_client(obj)
    return client.head(obj.path)


def object_exists(target: str | AzureObject) -> bool:
    """Check whether a blob exists at the URL.

    Parameters
    ----------
    target : str | AzureObject
        Azure Blob Storage URL or a pre-parsed AzureObject.

    Returns
    -------
    bool
        True if the blob exists, False otherwise.

    """
    obj = _azure_object(target)
    client = azure_client(obj)
    try:
        client.head(obj.path)
    except FileNotFoundError:
        return False
    else:
        return True


def get_object(target: str) -> obstore.Bytes:
    """Fetch a blob and return its contents.

    Parameters
    ----------
    target : str
        Azure Blob Storage URL.

    Returns
    -------
    obstore.Bytes
        The blob's contents.

    """
    obj = _azure_object(target)
    client = azure_client(obj)
    return client.get(obj.path).bytes()


def get_objects_parallel(targets: list[str]) -> list[obstore.Bytes]:
    """Fetch multiple blobs concurrently.

    Each fetch is retried up to three times on errors other than FileNotFoundError, which is raised immediately without
    retry.

    Parameters
    ----------
    targets : list[str]
        Azure Blob Storage URLs to fetch.

    Returns
    -------
    list[obstore.Bytes]
        Blob contents, in the same order as targets.

    Raises
    ------
    FileNotFoundError
        If any blob does not exist.
    OSError
        If any fetch fails three times consecutively for reasons other than the blob being missing.

    """

    def _fetch(target: str) -> obstore.Bytes:
        obj = _azure_object(target)
        client = azure_client(obj)
        last_exc = None
        for attempt in range(3):
            try:
                return client.get(obj.path).bytes()
            except FileNotFoundError:
                raise
            except Exception as e:
                last_exc = e
                LOG.exception("Fetch attempt %s/3 failed for %s.", attempt + 1, target)
        msg = f"Failed to fetch {target} after 3 attempts: {last_exc}"
        raise OSError(msg)

    with ThreadPoolExecutor(max_workers=len(targets)) as ex:
        return list(ex.map(_fetch, targets))


def upload(source: str, target: str, *args: bool | int, **kwargs: bool | int) -> Loader:
    """Upload a local file or directory to Azure Blob Storage via transfer.

    Parameters
    ----------
    source : str
        Local file or directory path.
    target : str
        Azure Blob Storage URL for the destination. Ends with '/' for a directory upload.
    *args : bool | int
        Additional positional arguments passed through to transfer.
    **kwargs : bool | int
        Additional keyword arguments passed through to transfer.

    Returns
    -------
    Loader
        Loader that performs and reports on the transfer when iterated.

    """
    _assert_azure_url(target)
    return transfer(source, target, *args, **kwargs)


def upload_file(source: str, target: str, overwrite: bool, resume: bool, verbosity: int) -> int:
    """Upload a single local file to Azure Blob Storage.

    Parameters
    ----------
    source : str
        Local file path to upload.
    target : str
        Azure Blob Storage URL for the destination blob.
    overwrite : bool
        If True, replace any existing blob at the destination.
    resume : bool
        If True, skip the upload when a blob of the expected size already exists at the destination.
    verbosity : int
        Verbosity level: 0 is silent, higher values show more progress.

    Returns
    -------
    int
        Number of bytes transferred.

    Raises
    ------
    ValueError
        If a blob already exists at the destination and neither overwrite nor resume is set.

    """
    obj = _azure_object(target)
    client = azure_client(obj)
    size = Path(source).stat().st_size
    if verbosity > 0:
        LOG.info("Upload %s to %s (%s)", source, target, bytes_to_human(size))

    try:
        remote_size = object_info(obj)["size"]
    except FileNotFoundError:
        remote_size = None

    if remote_size is not None:
        if remote_size != size and overwrite:
            LOG.warning(
                "%s already exists, but with different size, re-uploading (remote=%s, local=%s)",
                target,
                remote_size,
                size,
            )
        elif resume:
            return size

    if remote_size is not None and not overwrite and not resume:
        msg = f"{target} already exists, use 'overwrite' to replace or 'resume' to skip"
        raise ValueError(msg)

    chunk_size = 1024 * 1024 * 10
    total = size
    with (
        tqdm.tqdm(
            desc=obj.path,
            total=size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            leave=verbosity >= 2,
            delay=0 if verbosity > 0 else 10,
        ) as pbar,
        Path(source).open("rb") as f,
        closing(obstore.open_writer(client, obj.path, buffer_size=chunk_size)) as g,
    ):
        while total > 0:
            chunk = f.read(min(chunk_size, total))
            g.write(chunk)
            pbar.update(len(chunk))
            total -= len(chunk)
    return size


class AzureUpload(BaseUpload):
    """Transfer implementation for uploading local files and directories to Azure Blob Storage."""

    def get_temporary_target(self, target: str, _: str) -> str:  # type: ignore[override]
        """Return the final target unchanged.

        Azure Blob Storage uploads write directly to the destination.

        Parameters
        ----------
        target : str
            Azure Blob Storage URL for the destination.
        _ : str
            Ignored, kept for signature compatibility with the base class.

        Returns
        -------
        str
            The target URL, unchanged.

        """
        return target

    def rename_target(self, target: str, temporary_target: str) -> None:
        """No-op, Azure Blob Storage uploads write directly to the destination.

        Parameters
        ----------
        target : str
            Final Azure Blob Storage URL. Unused.
        temporary_target : str
            Temporary Azure Blob Storage URL. Unused.

        """

    def delete_target(self, target: str) -> None:
        """No-op, Azure Blob Storage uploads write directly to the destination.

        Parameters
        ----------
        target : str
            Azure Blob Storage URL. Unused.

        """

    def _transfer_file(
        self,
        source: str,
        target: str,
        overwrite: bool,
        resume: bool,
        verbosity: int,
        **_: object,
    ) -> int:
        """Upload a single local file to Azure Blob Storage.

        Parameters
        ----------
        source : str
            Local file path to upload.
        target : str
            Azure Blob Storage URL for the destination blob.
        overwrite : bool
            If True, replace any existing blob at the destination.
        resume : bool
            If True, skip the upload when a blob of the expected size already exists at the destination.
        verbosity : int
            Verbosity level: 0 is silent, higher values show more progress.
        **_ : object
            Ignored, kept for signature compatibility with the base class.

        Returns
        -------
        int
            Number of bytes transferred.

        """
        return upload_file(source, target, overwrite, resume, verbosity)


def download(
    source: str,
    target: str,
    *args: bool | int,
    **kwargs: bool | int,
) -> Loader:
    """Download a blob or prefix from Azure Blob Storage to a local path via transfer.

    Parameters
    ----------
    source : str
        Azure Blob Storage URL. Ends with '/' for a prefix download.
    target : str
        Local file or directory path.
    *args : bool | int
        Additional positional arguments passed through to transfer.
    **kwargs : bool | int
        Additional keyword arguments passed through to transfer.

    Returns
    -------
    Loader
        Loader that performs and reports on the transfer when iterated.

    """
    _assert_azure_url(source)
    return transfer(source, target, *args, **kwargs)


def download_file(source: str, target: str, overwrite: bool, resume: bool, verbosity: int) -> int:
    """Download a single blob to a local file path.

    The download is retried up to three times on errors other than FileNotFoundError, which is raised immediately
    without retry.

    Parameters
    ----------
    source : str
        Azure Blob Storage URL for the blob to download.
    target : str
        Local file path to write.
    overwrite : bool
        If True, replace any existing file at the target path.
    resume : bool
        If True, skip the download when a file of the expected size already exists at the target.
    verbosity : int
        Verbosity level: 0 is silent, higher values show more progress.

    Returns
    -------
    int
        Number of bytes transferred.

    Raises
    ------
    ValueError
        If a file already exists at the target and neither overwrite nor resume is set.
    FileNotFoundError
        If no blob exists at the source URL.
    OSError
        If the download fails three times consecutively for reasons other than the blob being missing.

    """
    obj = _azure_object(source)
    client = azure_client(obj)
    size = object_info(obj)["size"]

    if verbosity > 0:
        LOG.info("Download %s to %s (%s)", source, target, bytes_to_human(size))
    if overwrite:
        resume = False

    if (tgt_exists := Path(target).exists()) and resume:
        local_size = Path(target).stat().st_size
        if local_size != size:
            LOG.warning(
                "%s already exists with different size, re-downloading (remote=%s, local=%s)",
                target,
                size,
                local_size,
            )
        else:
            return size

    if tgt_exists and not overwrite and not resume:
        msg = f"{target} already exists, use 'overwrite' to replace or 'resume' to skip"
        raise ValueError(msg)

    last_exc = None
    for attempt in range(3):
        try:
            with (
                tqdm.tqdm(
                    desc=obj.path,
                    total=size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    leave=verbosity >= 2,
                    delay=0 if verbosity > 0 else 10,
                ) as pbar,
                Path(target).open("wb") as g,
            ):
                g.write(obstore.get(client, obj.path).bytes())
                pbar.update(size)
        except FileNotFoundError:
            raise
        except Exception as e:
            last_exc = e
            LOG.exception("Download attempt %s/3 failed for %s.", attempt + 1, source)
        else:
            return size

    msg = f"Failed to download {source} after 3 attempts: {last_exc}"
    raise OSError(msg)


class AzureDownload(BaseDownload):
    """Transfer implementation for downloading blobs and prefixes from Azure Blob Storage."""

    def copy(self, source: str, target: str, **kwargs: Any) -> None:  # noqa: ANN401
        """Copy a single blob or all blobs under a prefix to a local path.

        Dispatches to transfer_folder if source ends with '/', otherwise transfer_file.

        Parameters
        ----------
        source : str
            Azure Blob Storage URL. Treated as a prefix if it ends with '/', otherwise as a single blob.
        target : str
            Local file or directory path.
        **kwargs
            Additional keyword arguments forwarded to the underlying transfer.

        """
        _assert_azure_url(source)
        if source.endswith("/"):
            self.transfer_folder(source=source, target=target, **kwargs)
        else:
            self.transfer_file(source=source, target=target, **kwargs)

    def list_source(self, source: str) -> Iterable[ObjectMeta]:
        """List blobs under the source URL prefix.

        Parameters
        ----------
        source : str
            Azure Blob Storage URL used as a prefix.

        Yields
        ------
        ObjectMeta
            One item per blob under the prefix.

        """
        yield from _list_objects(source)

    def source_path(self, az_object: ObjectMeta, source: str) -> str:  # type: ignore[override]
        """Build the Azure Blob Storage URL for a single blob within source.

        Parameters
        ----------
        az_object : ObjectMeta
            Metadata for a single blob returned by list_source.
        source : str
            Azure Blob Storage URL used as a prefix.

        Returns
        -------
        str
            Full abfs:// URL for the blob, in container/path form.

        """
        obj = _azure_object(source)
        return f"{_ABFS_SCHEME}{obj.container}/{az_object['path']}"

    def target_path(self, az_object: ObjectMeta, source: str, target: str) -> str:  # type: ignore[override]
        """Build the local file path for a single blob, creating parent directories as needed.

        Parameters
        ----------
        az_object : ObjectMeta
            Metadata for a single blob returned by list_source.
        source : str
            Azure Blob Storage URL used as a prefix.
        target : str
            Local directory into which the blob should be written.

        Returns
        -------
        str
            Local path at which the blob will be written.

        """
        obj = _azure_object(source)
        # os.path.relpath (rather than Path.relative_to) so paths outside the source
        # prefix walk up with "..", avoiding the walk_up kwarg only added in 3.12
        local_path = Path(target) / os.path.relpath(az_object["path"], obj.path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        return str(local_path)

    def source_size(self, az_object: ObjectMeta) -> int:  # type: ignore[override]
        """Return the size in bytes of a single blob.

        Parameters
        ----------
        az_object : ObjectMeta
            Metadata for a single blob returned by list_source.

        Returns
        -------
        int
            Size of the blob in bytes.

        """
        return az_object["size"]

    def _transfer_file(
        self,
        source: str,
        target: str,
        overwrite: bool,
        resume: bool,
        verbosity: int,
        **_: object,
    ) -> int:
        """Download a single blob to a local file path.

        Parameters
        ----------
        source : str
            Azure Blob Storage URL for the blob to download.
        target : str
            Local file path to write.
        overwrite : bool
            If True, replace any existing file at the target path.
        resume : bool
            If True, skip the download when a file of the expected size already exists at the target.
        verbosity : int
            Verbosity level: 0 is silent, higher values show more progress.
        **_ : object
            Ignored, kept for signature compatibility with the base class.

        Returns
        -------
        int
            Number of bytes transferred.

        """
        return download_file(source, target, overwrite, resume, verbosity)
