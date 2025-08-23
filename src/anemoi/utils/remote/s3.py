# (C) Copyright 2024-2025 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""This module provides functions to upload, download, list and delete files and folders on S3.
The functions of this package expect that the AWS credentials are set up in the environment
typicaly by setting the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables or
by creating a `~/.aws/credentials` file. It is also possible to set the `endpoint_url` in the same file
to use a different S3 compatible service::

    [default]
    endpoint_url = https://some-storage.somewhere.world
    aws_access_key_id = xxxxxxxxxxxxxxxxxxxxxxxx
    aws_secret_access_key = xxxxxxxxxxxxxxxxxxxxxxxx

Alternatively, the `endpoint_url`, and keys can be set in one of
the `~/.config/anemoi/settings.toml`
or `~/.config/anemoi/settings-secrets.toml` files.
"""

import fnmatch
import logging
import os
import threading
from collections.abc import Iterable
from contextlib import closing
from typing import Any

import tqdm

from ..config import load_config
from ..humanize import bytes_to_human
from . import BaseDownload
from . import BaseUpload
from . import transfer

LOG = logging.getLogger(__name__)
SECRETS = ["aws_access_key_id", "aws_secret_access_key", "access_key_id", "secret_access_key"]


MIGRATE = {
    "aws_access_key_id": "access_key_id",
    "aws_secret_access_key": "secret_access_key",
}

CACHE = {}
LOCK = threading.Lock()


class S3Object:
    def __init__(self, url: str) -> None:
        """Initialise an S3Object from a URL.

        Parameters
        ----------
        url : str
            S3 URL (e.g., 's3://bucket/key').
        """
        self.url = url
        s3, empty, self.bucket, self.key = url.split("/", 3)
        assert s3 == "s3:"
        assert empty == ""
        self.dirname = f"s3://{self.bucket}"


def _s3_object(url_or_object: str | S3Object) -> S3Object:
    """Convert a string or S3Object to S3Object.

    Parameters
    ----------
    url_or_object : str or S3Object
        S3 URL or S3Object instance.

    Returns
    -------
    S3Object
        S3Object instance.
    """
    if isinstance(url_or_object, S3Object):
        return url_or_object

    if isinstance(url_or_object, str):
        return S3Object(url_or_object)

    raise TypeError(f"Invalid type for S3 object: {type(url_or_object)}")


def _hide_secrets(options: dict | list) -> dict | list:
    """Hide secret values in options.

    Parameters
    ----------
    options : dict or list
        Options possibly containing secrets.

    Returns
    -------
    dict or list
        Options with secrets hidden.
    """

    def __(k, v):
        if k in SECRETS:
            return "***"
        return v

    if isinstance(options, dict):
        return {k: __(k, v) for k, v in options.items()}

    if isinstance(options, list):
        return [_hide_secrets(o) for o in options]

    return options


def _s3_options(obj: str | S3Object) -> dict:
    """Get S3 options for a given object.

    Parameters
    ----------
    obj : str or S3Object
        S3 URL or S3Object instance.

    Returns
    -------
    dict
        S3 connection options.
    """

    obj = _s3_object(obj)

    with LOCK:
        if obj.dirname in CACHE:
            return CACHE[obj.dirname]

    options = {}

    # We may be accessing a different S3 compatible service
    # Use anemoi.config to get the configuration

    config = load_config(secrets=SECRETS)

    cfg = config.get("object-storage", {})
    candidate = None
    for k, v in cfg.items():
        if isinstance(v, (str, int, float, bool)):
            options[k] = v

        if isinstance(v, dict):
            if fnmatch.fnmatch(obj.bucket, k):
                if candidate is not None:
                    raise ValueError(
                        f"Multiple object storage configurations match {obj.    bucket}: {candidate} and {k}"
                    )
                candidate = k

    if candidate is not None:
        for k, v in cfg.get(candidate, {}).items():
            if isinstance(v, (str, int, float, bool)):
                options[k] = v

    type = options.pop("type", "s3")
    if type != "s3":
        raise ValueError(f"Unsupported object storage type {type}")

    for k, v in MIGRATE.items():
        if k in options:
            LOG.warning(f"Option '{k}' is deprecated, use '{v}' instead")
            options[v] = options.pop(k)

    LOG.info(f"Using S3 options: {_hide_secrets(options)}")

    with LOCK:
        CACHE[obj.dirname] = options

    return options


def s3_client(obj: str | S3Object) -> Any:
    """Create an S3 client for the given URL.

    Parameters
    ----------
    obj : str or S3Object
        S3 URL or S3Object instance.

    Returns
    -------
    Any
        S3 client instance.
    """

    import obstore

    obj = _s3_object(obj)
    options = _s3_options(obj)
    LOG.debug(f"Using S3 options: {_hide_secrets(options)}")
    return obstore.store.from_url(obj.dirname, **options)


def upload_file(source: str, target: str, overwrite: bool, resume: bool, verbosity: int) -> int:
    """Upload a file to S3.

    Parameters
    ----------
    source : str
        Local file path to upload.
    target : str
        S3 target URL.
    overwrite : bool
        Overwrite existing file if True.
    resume : bool
        Resume upload if True.
    verbosity : int
        Verbosity level.

    Returns
    -------
    int
        Number of bytes uploaded.
    """

    import obstore

    obj = _s3_object(target)

    s3 = s3_client(obj)
    size = os.path.getsize(source)

    if verbosity > 0:
        LOG.info(f"Upload {source} to {target} ({bytes_to_human(size)})")

    try:
        remote_size = object_info(obj)["size"]
    except FileNotFoundError:
        remote_size = None

    if remote_size is not None:
        if remote_size != size:
            LOG.warning(
                f"{target} already exists, but with different size, re-uploading (remote={remote_size}, local={size})"
            )
        elif resume:
            return size

    if remote_size is not None and not overwrite and not resume:
        raise ValueError(f"{target} already exists, use 'overwrite' to replace or 'resume' to skip")

    with tqdm.tqdm(
        desc=obj.key,
        total=size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        leave=verbosity >= 2,
        delay=0 if verbosity > 0 else 10,
    ) as pbar:
        chunk_size = 1024 * 1024
        total = size
        with open(source, "rb") as f:
            with closing(obstore.open_writer(s3, obj.key, buffer_size=chunk_size)) as g:
                while total > 0:
                    chunk = f.read(min(chunk_size, total))
                    g.write(chunk)
                    pbar.update(len(chunk))
                    total -= len(chunk)

    return size


def download_file(source: str, target: str, overwrite: bool, resume: bool, verbosity: int) -> int:
    """Download a file from S3.

    Parameters
    ----------
    source : str
        S3 source URL.
    target : str
        Local file path to save.
    overwrite : bool
        Overwrite existing file if True.
    resume : bool
        Resume download if True.
    verbosity : int
        Verbosity level.

    Returns
    -------
    int
        Number of bytes downloaded.
    """

    import obstore

    obj = _s3_object(source)

    s3 = s3_client(obj)

    size = object_info(source)["size"]

    if verbosity > 0:
        LOG.info(f"Download {source} to {target} ({bytes_to_human(size)})")

    if overwrite:
        resume = False

    if resume:
        if os.path.exists(target):
            local_size = os.path.getsize(target)
            if local_size != size:
                LOG.warning(f"{target} already with different size, re-downloading (remote={size}, local={local_size})")
            else:
                return size

    if os.path.exists(target) and not overwrite:
        raise ValueError(f"{target} already exists, use 'overwrite' to replace or 'resume' to skip")

    with tqdm.tqdm(
        desc=obj.key,
        total=size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        leave=verbosity >= 2,
        delay=0 if verbosity > 0 else 10,
    ) as pbar:
        chunk_size = 1024 * 1024
        total = size
        with closing(obstore.open_reader(s3, obj.key, buffer_size=chunk_size)) as f:
            with open(target, "wb") as g:
                while total > 0:
                    chunk = f.read(min(chunk_size, total))
                    g.write(chunk)
                    pbar.update(len(chunk))
                    total -= len(chunk)

    return size


def _list_objects(target: str, batch: bool = False) -> Iterable[list[dict]] | Iterable[dict]:

    import obstore

    """
    List objects in an S3 folder.

    Parameters
    ----------
    target : str
        S3 folder URL.
    batch : bool, optional
        Yield batches if True, else yield individual objects.

    Returns
    -------
    Iterable
        Iterable of objects or batches.
    """
    obj = _s3_object(target)

    s3 = s3_client(obj)

    for files in obstore.list(s3, obj.key + "/", chunk_size=1024):
        if batch:
            yield files
        else:
            yield from files


def delete_folder(target: str) -> None:

    import obstore

    """
    Delete all objects in an S3 folder.

    Parameters
    ----------
    target : str
        S3 folder URL.
    """
    obj = _s3_object(target)
    s3 = s3_client(obj)

    total = 0
    for batch in _list_objects(obj, batch=True):
        paths = [o["path"] for o in batch]
        LOG.info(f"Deleting {len(batch):,} objects from {target}")
        obstore.delete(s3, paths)
        total += len(batch)
        LOG.info(f"Deleted {len(batch):,} objects (total={total:,})")


def delete_file(target: str) -> None:
    import obstore

    obj = _s3_object(target)

    s3 = s3_client(obj)

    if not object_exists(obj):
        LOG.warning(f"{target} does not exist. Did you mean to delete a folder? Then add a trailing '/'")
        return

    LOG.info(f"Deleting {target}")
    obstore.delete(s3, obj.key)
    LOG.info(f"{target} is deleted")


def delete(target: str) -> None:
    """Delete a file or folder from S3.

    Parameters
    ----------
    target : str
        S3 URL (file or folder).
    """

    if target.endswith("/"):
        delete_folder(target)
    else:
        delete_file(target)


def list_folder(folder: str) -> Iterable[dict]:
    """List objects in an S3 folder.

    Parameters
    ----------
    folder : str
        S3 folder URL.

    Returns
    -------
    Iterable
        Iterable of objects.
    """
    return _list_objects(folder)


def object_info(target: str) -> dict:
    """Get information about an S3 object.

    Parameters
    ----------
    target : str
        S3 object URL.

    Returns
    -------
    dict
        Object metadata.
    """
    obj = _s3_object(target)
    s3 = s3_client(obj)
    return s3.head(obj.key)


def object_exists(target: str) -> bool:
    """Check if an S3 object exists.

    Parameters
    ----------
    target : str
        S3 object URL.

    Returns
    -------
    bool
        True if object exists, False otherwise.
    """
    obj = _s3_object(target)
    s3 = s3_client(obj)

    try:
        s3.head(obj.key)
        return True
    except FileNotFoundError:
        return False


def download(source: str, target: str, *args, **kwargs) -> None:
    """Download from S3 using transfer utility.

    Parameters
    ----------
    source : str
        S3 source URL.
    target : str
        Local target path.
    *args
        Additional arguments.
    **kwargs
        Additional keyword arguments.
    """

    assert source.startswith("s3://"), f"source {source} should start with 's3://'"
    return transfer(source, target, *args, **kwargs)


def upload(source: str, target: str, *args, **kwargs) -> None:
    """Upload to S3 using transfer utility.

    Parameters
    ----------
    source : str
        Local source path.
    target : str
        S3 target URL.
    *args
        Additional arguments.
    **kwargs
        Additional keyword arguments.
    """

    assert target.startswith("s3://"), f"target {target} should start with 's3://'"
    return transfer(source, target, *args, **kwargs)


##########################
# Generic transfer classes
##########################
class S3Upload(BaseUpload):

    def get_temporary_target(self, target: str, pattern: str) -> str:
        """Get temporary target path for upload.

        Parameters
        ----------
        target : str
            S3 target URL.
        pattern : str
            Pattern for temporary naming.

        Returns
        -------
        str
            Temporary target path.
        """
        return target

    def rename_target(self, target: str, temporary_target: str) -> None:
        """Rename temporary target to final target.

        Parameters
        ----------
        target : str
            Final target path.
        temporary_target : str
            Temporary target path.
        """
        pass

    def delete_target(self, target: str) -> None:
        """Delete target from S3.

        Parameters
        ----------
        target : str
            S3 target URL.
        """

        pass

    def _transfer_file(self, source: str, target: str, overwrite: bool, resume: bool, verbosity: int, **kwargs) -> int:
        """Transfer a file to S3.

        Parameters
        ----------
        source : str
            Local source path.
        target : str
            S3 target URL.
        overwrite : bool
            Overwrite existing file if True.
        resume : bool
            Resume upload if True.
        verbosity : int
            Verbosity level.
        kwargs : dict
            Additional keyword arguments.

        Returns
        -------
        int
            Number of bytes uploaded.
        """

        return upload_file(source, target, overwrite, resume, verbosity)


class S3Download(BaseDownload):

    def copy(self, source: str, target: str, **kwargs) -> None:
        """Copy file or folder from S3.

        Parameters
        ----------
        source : str
            S3 source URL.
        target : str
            Local target path.
        **kwargs
            Additional keyword arguments.
        """

        assert source.startswith("s3://")

        if source.endswith("/"):
            self.transfer_folder(source=source, target=target, **kwargs)
        else:
            self.transfer_file(source=source, target=target, **kwargs)

    def list_source(self, source: str) -> Iterable[dict]:
        """List objects in S3 source folder.

        Parameters
        ----------
        source : str
            S3 source folder URL.

        Returns
        -------
        Iterable
            Iterable of objects.
        """
        yield from _list_objects(source)

    def source_path(self, s3_object: dict, source: str) -> str:
        """Get S3 path for a source object.

        Parameters
        ----------
        s3_object : dict
            S3 object metadata.
        source : str
            S3 source folder URL.

        Returns
        -------
        str
            S3 object path.
        """
        object = _s3_object(source)
        return f"s3://{object.bucket}/{s3_object['path']}"

    def target_path(self, s3_object: dict, source: str, target: str) -> str:
        """Get local target path for an S3 object.

        Parameters
        ----------
        s3_object : dict
            S3 object metadata.
        source : str
            S3 source folder URL.
        target : str
            Local target folder.

        Returns
        -------
        str
            Local target path.
        """

        object = _s3_object(source)
        local_path = os.path.join(target, os.path.relpath(s3_object["path"], object.key))
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        return local_path

    def source_size(self, s3_object: dict) -> int:
        """Get size of S3 object.

        Parameters
        ----------
        s3_object : dict
            S3 object metadata.

        Returns
        -------
        int
            Size in bytes.
        """
        return s3_object["size"]

    def _transfer_file(self, source: str, target: str, overwrite: bool, resume: bool, verbosity: int, **kwargs) -> int:
        """Transfer a file from S3.

        Parameters
        ----------
        source : str
            S3 source URL.
        target : str
            Local target path.
        overwrite : bool
            Overwrite existing file if True.
        resume : bool
            Resume download if True.
        verbosity : int
            Verbosity level.
        kwargs : dict
            Additional keyword arguments.

        Returns
        -------
        int
            Number of bytes downloaded.
        """

        return download_file(source, target, overwrite, resume, verbosity)
