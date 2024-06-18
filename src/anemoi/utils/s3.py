# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
import logging
import os
from contextlib import closing

import boto3
import tqdm

LOG = logging.getLogger(__name__)


def _upload(source, target, overwrite=False, ignore_existing=False):
    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-uploading-files.html
    assert target.startswith("s3://")

    _, _, bucket, key = target.split("/", 3)

    LOG.info(f"Uploading {source} to {target}")
    s3_client = boto3.client("s3")

    if not overwrite:
        results = s3_client.list_objects(Bucket=bucket, Prefix=key)
        if results.get("Contents"):
            if ignore_existing:
                LOG.info(f"{target} already exists, skipping")
                return
            else:
                raise ValueError(f"{target} already exists, use --overwrite to replace")

    size = os.path.getsize(source)
    with closing(tqdm.tqdm(total=size, unit="B", unit_scale=True)) as t:
        s3_client.upload_file(source, bucket, key, Callback=lambda x: t.update(x))

    LOG.info(f"{target} is ready")


def upload(source, target, overwrite=False, ignore_existing=False):
    if os.path.isdir(source):
        for root, _, files in os.walk(source):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, source)
                s3_path = os.path.join(target, relative_path)
                _upload(local_path, s3_path, overwrite, ignore_existing)
    else:
        _upload(source, target, overwrite, ignore_existing)


def download(source, target, overwrite=False):
    assert source.startswith("s3://")

    _, _, bucket, key = source.split("/", 3)

    s3 = boto3.client("s3")
    response = s3.head_object(Bucket=bucket, Key=key)
    size = response["ContentLength"]

    if not overwrite:
        if os.path.exists(source) and os.path.getsize(source) == size:
            LOG.info(f"{source} already exists, skipping")
            return

    with closing(tqdm.tqdm(total=size, unit="B", unit_scale=True)) as t:
        s3.download_file(bucket, key, target, Callback=lambda x: t.update(x))
