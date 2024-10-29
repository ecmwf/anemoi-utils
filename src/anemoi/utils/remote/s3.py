# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
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

import logging
import os
import threading
from copy import deepcopy
from typing import Iterable

import tqdm

from ..config import load_config
from ..humanize import bytes_to_human
from . import BaseDownload
from . import BaseUpload

LOGGER = logging.getLogger(__name__)


# s3_clients are not thread-safe, so we need to create a new client for each thread

thread_local = threading.local()


def s3_client(bucket, region=None):
    import boto3
    from botocore import UNSIGNED
    from botocore.client import Config

    if not hasattr(thread_local, "s3_clients"):
        thread_local.s3_clients = {}

    key = f"{bucket}-{region}"

    boto3_config = dict(max_pool_connections=25)

    if key in thread_local.s3_clients:
        return thread_local.s3_clients[key]

    boto3_config = dict(max_pool_connections=25)

    if region:
        # This is using AWS

        options = {"region_name": region}

        # Anonymous access
        if not (
            os.path.exists(os.path.expanduser("~/.aws/credentials"))
            or ("AWS_ACCESS_KEY_ID" in os.environ and "AWS_SECRET_ACCESS_KEY" in os.environ)
        ):
            boto3_config["signature_version"] = UNSIGNED

    else:

        # We may be accessing a different S3 compatible service
        # Use anemoi.config to get the configuration

        options = {}
        config = load_config(secrets=["aws_access_key_id", "aws_secret_access_key"])

        cfg = config.get("object-storage", {})
        for k, v in cfg.items():
            if isinstance(v, (str, int, float, bool)):
                options[k] = v

        for k, v in cfg.get(bucket, {}).items():
            if isinstance(v, (str, int, float, bool)):
                options[k] = v

        type = options.pop("type", "s3")
        if type != "s3":
            raise ValueError(f"Unsupported object storage type {type}")

        if "config" in options:
            boto3_config.update(options["config"])
            del options["config"]
            from botocore.client import Config

    options["config"] = Config(**boto3_config)

    thread_local.s3_clients[key] = boto3.client("s3", **options)

    return thread_local.s3_clients[key]


class S3Upload(BaseUpload):

    def get_temporary_target(self, target, pattern):
        return target

    def rename_target(self, target, temporary_target):
        pass

    def delete_target(self, target):
        pass
        # delete(target)

    def _transfer_file(self, source, target, overwrite, resume, verbosity, threads, config=None):

        from botocore.exceptions import ClientError

        assert target.startswith("s3://")

        _, _, bucket, key = target.split("/", 3)
        s3 = s3_client(bucket)

        size = os.path.getsize(source)

        if verbosity > 0:
            LOGGER.info(f"{self.action} {source} to {target} ({bytes_to_human(size)})")

        try:
            results = s3.head_object(Bucket=bucket, Key=key)
            remote_size = int(results["ContentLength"])
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                raise
            remote_size = None

        if remote_size is not None:
            if remote_size != size:
                LOGGER.warning(
                    f"{target} already exists, but with different size, re-uploading (remote={remote_size}, local={size})"
                )
            elif resume:
                # LOGGER.info(f"{target} already exists, skipping")
                return size

        if remote_size is not None and not overwrite and not resume:
            raise ValueError(f"{target} already exists, use 'overwrite' to replace or 'resume' to skip")

        if verbosity > 0:
            with tqdm.tqdm(total=size, unit="B", unit_scale=True, unit_divisor=1024, leave=False) as pbar:
                s3.upload_file(source, bucket, key, Callback=lambda x: pbar.update(x), Config=config)
        else:
            s3.upload_file(source, bucket, key, Config=config)

        return size


class S3Download(BaseDownload):

    def copy(self, source, target, **kwargs):
        assert source.startswith("s3://")

        if source.endswith("/"):
            self.transfer_folder(source=source, target=target, **kwargs)
        else:
            self.transfer_file(source=source, target=target, **kwargs)

    def list_source(self, source):
        yield from _list_objects(source)

    def source_path(self, s3_object, source):
        _, _, bucket, _ = source.split("/", 3)
        return f"s3://{bucket}/{s3_object['Key']}"

    def target_path(self, s3_object, source, target):
        _, _, _, folder = source.split("/", 3)
        local_path = os.path.join(target, os.path.relpath(s3_object["Key"], folder))
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        return local_path

    def source_size(self, s3_object):
        return s3_object["Size"]

    def _transfer_file(self, source, target, overwrite, resume, verbosity, threads, config=None):
        # from boto3.s3.transfer import TransferConfig

        _, _, bucket, key = source.split("/", 3)
        s3 = s3_client(bucket)

        try:
            response = s3.head_object(Bucket=bucket, Key=key)
        except s3.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise ValueError(f"{source} does not exist ({bucket}, {key})")
            raise

        size = int(response["ContentLength"])

        if verbosity > 0:
            LOGGER.info(f"{self.action} {source} to {target} ({bytes_to_human(size)})")

        if overwrite:
            resume = False

        if resume:
            if os.path.exists(target):
                local_size = os.path.getsize(target)
                if local_size != size:
                    LOGGER.warning(
                        f"{target} already with different size, re-downloading (remote={size}, local={local_size})"
                    )
                else:
                    # if verbosity > 0:
                    #     LOGGER.info(f"{target} already exists, skipping")
                    return size

        if os.path.exists(target) and not overwrite:
            raise ValueError(f"{target} already exists, use 'overwrite' to replace or 'resume' to skip")

        if verbosity > 0:
            with tqdm.tqdm(total=size, unit="B", unit_scale=True, unit_divisor=1024, leave=False) as pbar:
                s3.download_file(bucket, key, target, Callback=lambda x: pbar.update(x), Config=config)
        else:
            s3.download_file(bucket, key, target, Config=config)

        return size


def _list_objects(target, batch=False):
    _, _, bucket, prefix = target.split("/", 3)
    s3 = s3_client(bucket)

    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" in page:
            objects = deepcopy(page["Contents"])
            if batch:
                yield objects
            else:
                yield from objects


def _delete_folder(target) -> None:
    _, _, bucket, _ = target.split("/", 3)
    s3 = s3_client(bucket)

    total = 0
    for batch in _list_objects(target, batch=True):
        LOGGER.info(f"Deleting {len(batch):,} objects from {target}")
        s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": o["Key"]} for o in batch]})
        total += len(batch)
        LOGGER.info(f"Deleted {len(batch):,} objects (total={total:,})")


def _delete_file(target) -> None:
    from botocore.exceptions import ClientError

    _, _, bucket, key = target.split("/", 3)
    s3 = s3_client(bucket)

    try:
        s3.head_object(Bucket=bucket, Key=key)
        exits = True
    except ClientError as e:
        if e.response["Error"]["Code"] != "404":
            raise
        exits = False

    if not exits:
        LOGGER.warning(f"{target} does not exist. Did you mean to delete a folder? Then add a trailing '/'")
        return

    LOGGER.info(f"Deleting {target}")
    s3.delete_object(Bucket=bucket, Key=key)
    LOGGER.info(f"{target} is deleted")


def delete(target) -> None:
    """Delete a file or a folder from S3.

    Parameters
    ----------
    target : str
        The URL of a file or a folder on S3. The url should start with 's3://'. If the URL ends with a '/' it is
        assumed to be a folder, otherwise it is assumed to be a file.
    """

    assert target.startswith("s3://")

    if target.endswith("/"):
        _delete_folder(target)
    else:
        _delete_file(target)


def list_folder(folder) -> Iterable:
    """List the sub folders in a folder on S3.

    Parameters
    ----------
    folder : str
        The URL of a folder on S3. The url should start with 's3://'.

    Returns
    -------
    list
        A list of the subfolders names in the folder.
    """

    assert folder.startswith("s3://")
    if not folder.endswith("/"):
        folder += "/"

    _, _, bucket, prefix = folder.split("/", 3)

    s3 = s3_client(bucket)
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
        if "CommonPrefixes" in page:
            yield from [folder + _["Prefix"] for _ in page.get("CommonPrefixes")]


def object_info(target) -> dict:
    """Get information about an object on S3.

    Parameters
    ----------
    target : str
        The URL of a file or a folder on S3. The url should start with 's3://'.

    Returns
    -------
    dict
        A dictionary with information about the object.
    """

    _, _, bucket, key = target.split("/", 3)
    s3 = s3_client(bucket)

    try:
        return s3.head_object(Bucket=bucket, Key=key)
    except s3.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise ValueError(f"{target} does not exist")
        raise


def object_acl(target) -> dict:
    """Get information about an object's ACL on S3.

    Parameters
    ----------
    target : str
        The URL of a file or a folder on S3. The url should start with 's3://'.

    Returns
    -------
    dict
        A dictionary with information about the object's ACL.
    """

    _, _, bucket, key = target.split("/", 3)
    s3 = s3_client()

    return s3.get_object_acl(Bucket=bucket, Key=key)


def download(source, target, *args, **kwargs):
    from . import transfer

    assert source.startswith("s3://"), f"source {source} should start with 's3://'"
    return transfer(source, target, *args, **kwargs)


def upload(source, target, *args, **kwargs):
    from . import transfer

    assert target.startswith("s3://"), f"target {target} should start with 's3://'"
    return transfer(source, target, *args, **kwargs)
