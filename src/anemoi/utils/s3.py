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
from contextlib import closing

import tqdm

LOGGER = logging.getLogger(__name__)


# s3_clients are not thread-safe, so we need to create a new client for each thread

thread_local = threading.local()


def _s3_client():
    import boto3

    if not hasattr(thread_local, "s3_client"):
        thread_local.s3_client = boto3.client("s3")
    return thread_local.s3_client


def _upload_file(source, target, overwrite=False, ignore_existing=False, show_progress=1):
    from botocore.exceptions import ClientError

    assert target.startswith("s3://")

    _, _, bucket, key = target.split("/", 3)

    # LOGGER.info(f"Uploading {source} to {target}")
    s3_client = _s3_client()

    size = os.path.getsize(source)
    try:
        results = s3_client.head_object(Bucket=bucket, Key=key)
        remote_size = int(results["ContentLength"])
    except ClientError as e:
        if e.response["Error"]["Code"] != "404":
            raise
        remote_size = None

    if remote_size is not None:
        if remote_size != size:
            LOGGER.warning(f"{target} already exists, but with different size, re-uploading")
            overwrite = True

        if ignore_existing:
            LOGGER.info(f"{target} already exists, skipping")
            return

    if remote_size is not None and not overwrite:
        raise ValueError(f"{target} already exists, use 'overwrite' to replace or 'ignore_existing' to skip")

    if show_progress > 0:
        with closing(tqdm.tqdm(total=size, unit="B", unit_scale=True, leave=False)) as t:
            s3_client.upload_file(source, bucket, key, Callback=lambda x: t.update(x))
    else:
        s3_client.upload_file(source, bucket, key)


def _local_file_list(source):
    for root, _, files in os.walk(source):
        for file in files:
            yield os.path.join(root, file)


def _upload_folder(source, target, overwrite=False, ignore_existing=False, threads=1, show_progress=1):

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        try:
            LOGGER.info(f"Uploading {source} to {target}")

            futures = []
            for local_path in _local_file_list(source):
                relative_path = os.path.relpath(local_path, source)
                s3_path = os.path.join(target, relative_path)
                futures.append(executor.submit(_upload_file, local_path, s3_path, overwrite, ignore_existing))

                if len(futures) % 10000 == 0:
                    LOGGER.info(f"Preparing upload, {len(futures):,} files...")
                    done, _ = concurrent.futures.wait(
                        futures,
                        timeout=0.001,
                        return_when=concurrent.futures.FIRST_EXCEPTION,
                    )
                    # Trigger exceptions if any
                    for n in done:
                        n.result()

            LOGGER.info(f"Uploading {len(futures):,} files")

            if show_progress > 0:
                for future in tqdm.tqdm(futures, total=len(futures)):
                    future.result()
            else:
                for future in futures:
                    future.result()

        except Exception:
            executor.shutdown(wait=False, cancel_futures=True)
            raise


def upload(source, target, overwrite=False, ignore_existing=False, threads=1, show_progress=True):
    """Upload a file or a folder to S3.

    Parameters
    ----------
    source : str
        A path to a file or a folder to upload.
    target : str
        A URL to a file or a folder on S3. The url should start with 's3://'.
    overwrite : bool, optional
        If the data is alreay on S3 it will be overwritten, by default False
    ignore_existing : bool, optional
        If the data is alreay on S3 it will not be uploaded, unless the remote file
        has a different size, by default False
    threads : int, optional
        The number of threads to use when uploading a directory, by default 1
    """
    if os.path.isdir(source):
        _upload_folder(source, target, overwrite, ignore_existing, threads)
    else:
        _upload_file(source, target, overwrite, ignore_existing)


def _download_file(source, target, overwrite=False, ignore_existing=False, show_progress=0):
    s3_client = _s3_client()
    _, _, bucket, key = source.split("/", 3)

    response = s3_client.head_object(Bucket=bucket, Key=key)
    size = int(response["ContentLength"])

    if os.path.exists(target):

        if os.path.exists(target) and os.path.getsize(target) != size:
            LOGGER.info(f"{target} already with different size, re-downloading")
            overwrite = True

        if not overwrite and not ignore_existing:
            raise ValueError(f"{target} already exists, use 'overwrite' to replace or 'ignore_existing' to skip")

        if ignore_existing:
            LOGGER.info(f"{target} already exists, skipping")
            return

    if show_progress > 0:
        with closing(tqdm.tqdm(total=size, unit="B", unit_scale=True, leave=False)) as t:
            s3_client.download_file(bucket, key, target, Callback=lambda x: t.update(x))
    else:
        s3_client.download_file(bucket, key, target)


def _download_folder(source, target, *, overwrite=False, ignore_existing=False, show_progress=1, threads=1):
    assert show_progress > 0
    source = source.rstrip("/")
    _, _, bucket, folder = source.split("/", 3)

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        try:
            LOGGER.info(f"Downloading {source} to {target}")

            futures = []
            for o in _list_objects(source):
                name = o["Key"]
                local_path = os.path.join(target, os.path.relpath(name, folder))
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                futures.append(
                    executor.submit(
                        _download_file,
                        f"s3://{bucket}/{name}",
                        local_path,
                        overwrite,
                        ignore_existing,
                        show_progress - 1,
                    )
                )
                if len(futures) % 10000 == 0:
                    LOGGER.info(f"Preparing download, {len(futures):,} files...")
                    done, _ = concurrent.futures.wait(
                        futures,
                        timeout=0.001,
                        return_when=concurrent.futures.FIRST_EXCEPTION,
                    )
                    # Trigger exceptions if any
                    for n in done:
                        n.result()

            LOGGER.info(f"Downloading {len(futures):,} files %s", show_progress)
            if show_progress > 0:
                for future in tqdm.tqdm(futures, total=len(futures)):
                    future.result()
            else:
                for future in futures:
                    future.result()

        except Exception:
            executor.shutdown(wait=False, cancel_futures=True)
            raise


def download(source, target, *, overwrite=False, ignore_existing=False, show_progress=1, threads=1):
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
    ignore_existing : bool, optional
        If the data is alreay on local it will not be downloaded, unless the remote file
        has a different size, by default False
    threads : int, optional
        The number of threads to use when downloading a directory, by default 1
    """
    assert source.startswith("s3://")

    if source.endswith("/"):
        _download_folder(
            source,
            target,
            overwrite=overwrite,
            ignore_existing=ignore_existing,
            show_progress=show_progress,
            threads=threads,
        )
    else:
        _download_file(
            source, target, overwrite=overwrite, ignore_existing=ignore_existing, show_progress=show_progress
        )


def _list_objects(target, batch=False):
    s3_client = _s3_client()
    _, _, bucket, prefix = target.split("/", 3)

    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" in page:
            objects = [{"Key": obj["Key"]} for obj in page["Contents"]]
            if batch:
                yield objects
            else:
                yield from objects


def _delete_folder(target):
    s3_client = _s3_client()
    _, _, bucket, _ = target.split("/", 3)

    for batch in _list_objects(target, batch=True):
        s3_client.delete_objects(Bucket=bucket, Delete={"Objects": batch})
        LOGGER.info(f"Deleted {len(batch)} objects")


def _delete_file(target):
    s3_client = _s3_client()
    _, _, bucket, key = target.split("/", 3)

    LOGGER.info(f"Deleting {target}")
    s3_client.delete_object(Bucket=bucket, Key=key)
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


def list_folders(folder):
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

    s3_client = _s3_client()
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
        if "CommonPrefixes" in page:
            yield from [folder + _["Prefix"] for _ in page.get("CommonPrefixes")]
