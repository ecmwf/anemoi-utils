# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import boto3
import tqdm
from botocore.exceptions import ClientError

LOG = logging.getLogger(__name__)


# s3_clients are not thread-safe, so we need to create a new client for each thread

thread_local = threading.local()


def get_s3_client():
    if not hasattr(thread_local, "s3_client"):
        thread_local.s3_client = boto3.client("s3")
    return thread_local.s3_client


def _upload_file(source, target, overwrite=False, ignore_existing=False):

    assert target.startswith("s3://")

    _, _, bucket, key = target.split("/", 3)

    LOG.info(f"Uploading {source} to {target}")
    s3_client = get_s3_client()

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
            LOG.warning(f"{target} already exists, but with different size, re-uploading")
            overwrite = True

        if ignore_existing:
            LOG.info(f"{target} already exists, skipping")
            return

    if remote_size is not None and not overwrite:
        raise ValueError(f"{target} already exists, use 'overwrite' to replace or 'ignore_existing' to skip")

    with closing(tqdm.tqdm(total=size, unit="B", unit_scale=True, leave=False)) as t:
        s3_client.upload_file(source, bucket, key, Callback=lambda x: t.update(x))


def _local_file_list(source):
    for root, _, files in os.walk(source):
        for file in files:
            yield os.path.join(root, file)


def _upload_folder(source, target, overwrite=False, ignore_existing=False, threads=1):
    total = sum(1 for _ in _local_file_list(source))

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for local_path in _local_file_list(source):
            relative_path = os.path.relpath(local_path, source)
            s3_path = os.path.join(target, relative_path)
            futures.append(executor.submit(_upload_file, local_path, s3_path, overwrite, ignore_existing))

        for future in tqdm.tqdm(futures, total=total):
            future.result()


def upload(source, target, overwrite=False, ignore_existing=False, threads=1):
    if os.path.isdir(source):
        _upload_folder(source, target, overwrite, ignore_existing, threads)
    else:
        _upload_file(source, target, overwrite, ignore_existing)


def _download_file(source, target, overwrite=False):
    s3_client = get_s3_client()
    _, _, bucket, key = source.split("/", 3)

    response = s3_client.head_object(Bucket=bucket, Key=key)
    size = int(response["ContentLength"])

    if not overwrite:
        if os.path.exists(target) and os.path.getsize(target) == size:
            LOG.info(f"{target} already exists, skipping")
            return

    with closing(tqdm.tqdm(total=size, unit="B", unit_scale=True, leave=False)) as t:
        s3_client.download_file(bucket, key, target, Callback=lambda x: t.update(x))


def _download_folder(source, target, overwrite=False, threads=1):
    source = source.rstrip("/")
    _, _, bucket, folder = source.split("/", 3)
    total = _count_objects_in_folder(source)

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for o in _list_folder(source):
            name = o["Key"]
            local_path = os.path.join(target, os.path.relpath(name, folder))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            futures.append(executor.submit(_download_file, f"s3://{bucket}/{name}", local_path, overwrite))

        for future in tqdm.tqdm(futures, total=total):
            future.result()


def download(source, target, overwrite=False, threads=1):
    assert source.startswith("s3://")

    if source.endswith("/"):
        _download_folder(source, target, overwrite, threads)
    else:
        _download_file(source, target, overwrite)


def _list_folder(target, batch=False):
    s3_client = get_s3_client()
    _, _, bucket, prefix = target.split("/", 3)

    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" in page:
            objects = [{"Key": obj["Key"]} for obj in page["Contents"]]
            if batch:
                yield objects
            else:
                yield from objects


def _count_objects_in_folder(target):
    return sum(len(_) for _ in _list_folder(target, batch=True))


def _delete_folder(target, threads):
    s3_client = get_s3_client()
    _, _, bucket, _ = target.split("/", 3)

    for batch in _list_folder(target, batch=True):
        s3_client.delete_objects(Bucket=bucket, Delete={"Objects": batch})
        LOG.info(f"Deleted {len(batch)} objects")


def _delete_file(target):
    s3_client = get_s3_client()
    _, _, bucket, key = target.split("/", 3)

    LOG.info(f"Deleting {target}")
    s3_client.delete_object(Bucket=bucket, Key=key)
    LOG.info(f"{target} is deleted")


def delete(target, threads=1):
    """Delete a file or a folder from S3."""

    assert target.startswith("s3://")

    if target.endswith("/"):
        _delete_folder(target, threads)
    else:
        _delete_file(target)


def list_folder(target, batch=False):
    assert target.startswith("s3://")
    return _list_folder(target, batch)


def count_objects_in_folder(target):
    assert target.startswith("s3://")
    return _count_objects_in_folder(target)
