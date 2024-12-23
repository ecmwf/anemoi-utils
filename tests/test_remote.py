# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
import shutil

import pytest

from anemoi.utils.remote import TransferMethodNotImplementedError
from anemoi.utils.remote import _find_transfer_class
from anemoi.utils.remote import transfer

IN_CI = (os.environ.get("GITHUB_WORKFLOW") is not None) or (os.environ.get("IN_CI_HPC") is not None)

LOCAL = [
    "/absolute/path/to/file",
    "relative/file",
    "/absolute/path/to/dir/",
    "relative/dir/",
    ".",
    "..",
    "./",
    "file",
    "dir/",
    "/dir/",
    "/dir",
    "/file",
]
S3 = ["s3://bucket/key/", "s3://bucket/key"]
SSH = [
    "ssh://hostname:/absolute/file",
    "ssh://hostname:relative/file",
    "ssh://hostname:/absolute/dir/",
    "ssh://hostname:relative/dir/",
]

ROOT_S3_READ = "s3://ml-tests/test-data/anemoi-utils/pytest/transfer"
ROOT_S3_WRITE = f"s3://ml-tmp/anemoi-utils/pytest/transfer/test-{os.getpid()}"

LOCAL_TEST_DATA = os.path.dirname(__file__) + "/test-transfer-data"


@pytest.mark.parametrize("source", LOCAL)
@pytest.mark.parametrize("target", S3)
def test_transfer_find_s3_upload(source, target):
    from anemoi.utils.remote.s3 import S3Upload

    assert _find_transfer_class(source, target) == S3Upload


@pytest.mark.parametrize("source", S3)
@pytest.mark.parametrize("target", LOCAL)
def test_transfer_find_s3_download(source, target):
    from anemoi.utils.remote.s3 import S3Download

    assert _find_transfer_class(source, target) == S3Download


@pytest.mark.parametrize("source", LOCAL)
@pytest.mark.parametrize("target", SSH)
def test_transfer_find_ssh_upload(source, target):
    from anemoi.utils.remote.ssh import RsyncUpload

    assert _find_transfer_class(source, target) == RsyncUpload


@pytest.mark.parametrize("source", S3 + SSH)
@pytest.mark.parametrize("target", S3 + SSH)
def test_transfer_find_none(source, target):
    with pytest.raises(TransferMethodNotImplementedError):
        assert _find_transfer_class(source, target)


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
def test_transfer_zarr_s3_to_local(tmpdir):
    source = "s3://ml-datasets/aifs-ea-an-oper-0001-mars-20p0-2000-2000-12h-v0-TESTING2.zarr/"
    tmp = tmpdir.strpath + "/test"

    transfer(source, tmp)
    with pytest.raises(ValueError, match="already exists"):
        transfer(source, tmp)

    transfer(source, tmp, resume=True)
    transfer(source, tmp, overwrite=True)


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
def test_transfer_zarr_local_to_s3(tmpdir):
    fixture = "s3://ml-datasets/aifs-ea-an-oper-0001-mars-20p0-2000-2000-12h-v0-TESTING2.zarr/"
    source = tmpdir.strpath + "/test"
    target = ROOT_S3_WRITE + "/test.zarr"

    transfer(fixture, source)
    transfer(source, target)

    with pytest.raises(ValueError, match="already exists"):
        transfer(source, target)

    transfer(source, target, resume=True)
    transfer(source, target, overwrite=True)


def _delete_file_or_directory(path):
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    else:
        if os.path.exists(path):
            os.remove(path)


def compare(local1, local2):
    if os.path.isdir(local1):
        for root, dirs, files in os.walk(local1):
            for file in files:
                file1 = os.path.join(root, file)
                file2 = file1.replace(local1, local2)
                assert os.path.exists(file2)
                with open(file1, "rb") as f1, open(file2, "rb") as f2:
                    assert f1.read() == f2.read()
    else:
        with open(local1, "rb") as f1, open(local2, "rb") as f2:
            assert f1.read() == f2.read()


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
@pytest.mark.parametrize("path", ["directory/", "file"])
def test_transfer_local_to_s3_to_local(path):
    local = LOCAL_TEST_DATA + "/" + path
    remote = ROOT_S3_WRITE + "/" + path
    local2 = LOCAL_TEST_DATA + "-copy-" + path

    transfer(local, remote, overwrite=True)
    transfer(local, remote, resume=True)
    with pytest.raises(ValueError, match="already exists"):
        transfer(local, remote)

    _delete_file_or_directory(local2)
    transfer(remote, local2)
    with pytest.raises(ValueError, match="already exists"):
        transfer(remote, local2)
    transfer(local, remote, overwrite=True)
    transfer(local, remote, resume=True)

    compare(local, local2)

    _delete_file_or_directory(local2)


@pytest.mark.skipif(IN_CI, reason="Test requires ssh access to localhost")
@pytest.mark.parametrize("path", ["directory", "file"])
@pytest.mark.parametrize("temporary_target", [True, False])
def test_transfer_local_to_ssh(path, temporary_target):
    local = LOCAL_TEST_DATA + "/" + path
    remote_path = LOCAL_TEST_DATA + "-as-ssh-" + path
    assert os.path.isabs(remote_path), remote_path

    remote = "ssh://localhost:" + remote_path

    transfer(local, remote, temporary_target=temporary_target)
    transfer(local, remote, temporary_target=temporary_target)

    compare(local, remote_path)

    _delete_file_or_directory(remote_path)


if __name__ == "__main__":
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
