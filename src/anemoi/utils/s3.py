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

"""

import concurrent
import logging
import os
import threading
from copy import deepcopy

import tqdm

from .config import check_config_mode
from .config import load_config
from .humanize import bytes

LOGGER = logging.getLogger(__name__)


# s3_clients are not thread-safe, so we need to create a new client for each thread

thread_local = threading.local()


def s3_client(bucket):
    import boto3

    config = load_config()
    if "object-storage" in config:
        check_config_mode()

    if not hasattr(thread_local, "s3_clients"):
        thread_local.s3_clients = {}

    if bucket not in thread_local.s3_clients:

        options = {}
        options.update(config.get("object-storage", {}))
        options.update(config.get("object-storage", {}).get(bucket, {}))

        type = options.pop("type", "s3")
        if type != "s3":
            raise ValueError(f"Unsupported object storage type {type}")

        if "config" in options:
            from botocore.client import Config

            options["config"] = Config(**options["config"])
            del options["config"]

        thread_local.s3_clients[bucket] = boto3.client("s3", **options)

    return thread_local.s3_clients[bucket]


class Transfer:

    def transfer_folder(self, *, source, target, overwrite=False, resume=False, verbosity=1, threads=1):
        assert verbosity == 1, verbosity

        # from boto3.s3.transfer import TransferConfig
        # config = TransferConfig(use_threads=False)
        config = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            try:
                if verbosity > 0:
                    LOGGER.info(f"{self.action} {source} to {target}")

                total = 0

                futures = []
                for name in self.list_source(source):

                    futures.append(
                        executor.submit(
                            self.transfer_file,
                            source=self.source_path(name, source),
                            target=self.target_path(name, source, target),
                            overwrite=overwrite,
                            resume=resume,
                            verbosity=verbosity - 1,
                            config=config,
                        )
                    )
                    total += self.source_size(name)

                    if len(futures) % 10000 == 0:
                        if verbosity > 0:
                            LOGGER.info(f"Preparing transfer, {len(futures):,} files... ({bytes(total)})")
                        done, _ = concurrent.futures.wait(
                            futures,
                            timeout=0.001,
                            return_when=concurrent.futures.FIRST_EXCEPTION,
                        )
                        # Trigger exceptions if any
                        for future in done:
                            future.result()

                if verbosity > 0:
                    LOGGER.info(f"{self.action} {len(futures):,} files ({bytes(total)})")
                    with tqdm.tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024) as pbar:
                        for future in futures:
                            pbar.update(future.result())
                else:
                    for future in futures:
                        future.result()

            except Exception:
                executor.shutdown(wait=False, cancel_futures=True)
                raise


class Upload(Transfer):
    action = "Uploading"

    def list_source(self, source):
        for root, _, files in os.walk(source):
            for file in files:
                yield os.path.join(root, file)

    def source_path(self, local_path, source):
        return local_path

    def target_path(self, source_path, source, target):
        relative_path = os.path.relpath(source_path, source)
        s3_path = os.path.join(target, relative_path)
        return s3_path

    def source_size(self, local_path):
        return os.path.getsize(local_path)

    def transfer_file(self, source, target, overwrite, resume, verbosity, config=None):
        try:
            return self._transfer_file(source, target, overwrite, resume, verbosity, config=config)
        except Exception as e:
            LOGGER.exception(f"Error transferring {source} to {target}")
            LOGGER.error(e)
            raise

    def _transfer_file(self, source, target, overwrite, resume, verbosity, config=None):

        from botocore.exceptions import ClientError

        assert target.startswith("s3://")

        _, _, bucket, key = target.split("/", 3)
        s3 = s3_client(bucket)

        size = os.path.getsize(source)

        if verbosity > 0:
            LOGGER.info(f"{self.action} {source} to {target} ({bytes(size)})")

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


class Download(Transfer):
    action = "Downloading"

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

    def transfer_file(self, source, target, overwrite, resume, verbosity, config=None):
        try:
            return self._transfer_file(source, target, overwrite, resume, verbosity, config=config)
        except Exception as e:
            LOGGER.exception(f"Error transferring {source} to {target}")
            LOGGER.error(e)
            raise

    def _transfer_file(self, source, target, overwrite, resume, verbosity, config=None):
        # from boto3.s3.transfer import TransferConfig

        _, _, bucket, key = source.split("/", 3)
        s3 = s3_client(bucket)

        try:
            response = s3.head_object(Bucket=bucket, Key=key)
        except s3.exceptions.ClientError as e:
            print(e.response["Error"]["Code"], e.response["Error"]["Message"], bucket, key)
            if e.response["Error"]["Code"] == "404":
                raise ValueError(f"{source} does not exist ({bucket}, {key})")
            raise

        size = int(response["ContentLength"])

        if verbosity > 0:
            LOGGER.info(f"Downloading {source} to {target} ({bytes(size)})")

        if overwrite:
            resume = False

        if resume:
            if os.path.exists(target):
                local_size = os.path.getsize(target)
                if local_size != size:
                    LOGGER.warning(
                        f"{target} already with different size, re-downloading (remote={size}, local={size})"
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


def upload(source, target, *, overwrite=False, resume=False, verbosity=1, threads=1):
    """Upload a file or a folder to S3.

    Parameters
    ----------
    source : str
        A path to a file or a folder to upload.
    target : str
        A URL to a file or a folder on S3. The url should start with 's3://'.
    overwrite : bool, optional
        If the data is alreay on S3 it will be overwritten, by default False
    resume : bool, optional
        If the data is alreay on S3 it will not be uploaded, unless the remote file
        has a different size, by default False
    threads : int, optional
        The number of threads to use when uploading a directory, by default 1
    """

    uploader = Upload()
    if os.path.isdir(source):
        uploader.transfer_folder(
            source=source, target=target, overwrite=overwrite, resume=resume, verbosity=verbosity, threads=threads
        )
    else:
        uploader.transfer_file(source=source, target=target, overwrite=overwrite, resume=resume, verbosity=verbosity)


def download(source, target, *, overwrite=False, resume=False, verbosity=1, threads=1):
    """Download a file or a folder from S3.

    Parameters
    ----------
    source : str
        The URL of a file or a folder on S3. The url should start with 's3://'. If the URL ends with a '/' it is
        assumed to be a folder, otherwise it is assumed to be a file.
    target : str
        The local path where the file or folder will be downloaded.
    overwrite : bool, optional
        If false, files which have already been download will be skipped, unless their size
        does not match their size on S3 , by default False
    resume : bool, optional
        If the data is alreay on local it will not be downloaded, unless the remote file
        has a different size, by default False
    threads : int, optional
        The number of threads to use when downloading a directory, by default 1
    """
    assert source.startswith("s3://")

    downloader = Download()

    if source.endswith("/"):
        downloader.transfer_folder(
            source=source,
            target=target,
            overwrite=overwrite,
            resume=resume,
            verbosity=verbosity,
            threads=threads,
        )
    else:
        downloader.transfer_file(
            source=source,
            target=target,
            overwrite=overwrite,
            resume=resume,
            verbosity=verbosity,
        )


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


def _delete_folder(target):
    _, _, bucket, _ = target.split("/", 3)
    s3 = s3_client(bucket)

    total = 0
    for batch in _list_objects(target, batch=True):
        LOGGER.info(f"Deleting {len(batch):,} objects from {target}")
        s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": o["Key"]} for o in batch]})
        total += len(batch)
        LOGGER.info(f"Deleted {len(batch):,} objects (total={total:,})")


def _delete_file(target):
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
    print(s3.delete_object(Bucket=bucket, Key=key))
    LOGGER.info(f"{target} is deleted")


def delete(target):
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


def list_folder(folder):
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


def object_info(target):
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


def object_acl(target):
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
