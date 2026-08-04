# (C) Copyright 2024-2026 Anemoi contributors.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
import shutil
import sys
import uuid

import pytest

from anemoi.utils.remote import TransferMethodNotImplementedError
from anemoi.utils.remote import _find_transfer_class
from anemoi.utils.remote import transfer
from anemoi.utils.testing import skip_missing_packages
from tests.helpers.azurite import AZURITE_CONTAINER
from tests.helpers.azurite import AZURITE_ENDPOINT
from tests.helpers.azurite import azurite_reachable

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
AZ = ["abfs://container/path/", "abfs://container@account.blob.core.windows.net/path"]
S3 = ["s3://bucket/key/", "s3://bucket/key"]
SSH = [
    "ssh://hostname:/absolute/file",
    "ssh://hostname:relative/file",
    "ssh://hostname:/absolute/dir/",
    "ssh://hostname:relative/dir/",
]

ROOT_S3_READ = "s3://ml-tests/test-data/anemoi-utils/pytest/transfer"
ROOT_S3_WRITE = "s3://ml-tmp/anemoi-utils/pytest/transfer-tests"
LOCAL_TEST_DATA = os.path.dirname(__file__) + "/test-transfer-data"


@pytest.mark.parametrize("source", LOCAL)
@pytest.mark.parametrize("target", S3)
def test_transfer_find_s3_upload(source: str, target: str) -> None:
    """Test finding the S3 upload transfer class.

    Parameters
    ----------
    source : str
        The source path
    target : str
        The target path
    """
    from anemoi.utils.remote.s3 import S3Upload

    assert _find_transfer_class(source, target) == S3Upload


@pytest.mark.parametrize("source", LOCAL)
@pytest.mark.parametrize("target", AZ)
def test_transfer_find_az_upload(source: str, target: str) -> None:
    """Test finding the Azure Blob Storage upload transfer class.

    Parameters
    ----------
    source : str
        The source path
    target : str
        The target path
    """
    from anemoi.utils.remote.az import AzureUpload

    assert _find_transfer_class(source, target) == AzureUpload


@pytest.mark.parametrize("source", S3)
@pytest.mark.parametrize("target", LOCAL)
def test_transfer_find_s3_download(source: str, target: str) -> None:
    """Test finding the S3 download transfer class.

    Parameters
    ----------
    source : str
        The source path
    target : str
        The target path
    """
    from anemoi.utils.remote.s3 import S3Download

    assert _find_transfer_class(source, target) == S3Download


@pytest.mark.parametrize("source", AZ)
@pytest.mark.parametrize("target", LOCAL)
def test_transfer_find_az_download(source: str, target: str) -> None:
    """Test finding the Azure Blob Storage download transfer class.

    Parameters
    ----------
    source : str
        The source path
    target : str
        The target path
    """
    from anemoi.utils.remote.az import AzureDownload

    assert _find_transfer_class(source, target) == AzureDownload


@pytest.mark.parametrize("source", LOCAL)
@pytest.mark.parametrize("target", SSH)
def test_transfer_find_ssh_upload(source: str, target: str) -> None:
    """Test finding the SSH upload transfer class.

    Parameters
    ----------
    source : str
        The source path
    target : str
        The target path
    """
    from anemoi.utils.remote.ssh import RsyncUpload

    assert _find_transfer_class(source, target) == RsyncUpload


@pytest.mark.parametrize("source", AZ + S3 + SSH)
@pytest.mark.parametrize("target", AZ + S3 + SSH)
def test_transfer_find_none(source: str, target: str) -> None:
    """Test that no transfer class is found for unsupported transfers.

    Parameters
    ----------
    source : str
        The source path
    target : str
        The target path
    """
    with pytest.raises(TransferMethodNotImplementedError):
        assert _find_transfer_class(source, target)


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
@skip_missing_packages("obstore")
def test_transfer_zarr_s3_to_local(tmpdir: pytest.TempPathFactory) -> None:
    """Test transferring a Zarr file from S3 to local.

    Parameters
    ----------
    tmpdir : pytest.TempPathFactory
        Temporary directory factory
    """
    source = "s3://ml-datasets/aifs-ea-an-oper-0001-mars-20p0-2000-2000-12h-v0-TESTING2.zarr/"
    tmp = tmpdir.strpath + "/test"

    transfer(source, tmp)
    with pytest.raises(ValueError, match="already exists"):
        transfer(source, tmp)

    transfer(source, tmp, resume=True)
    transfer(source, tmp, overwrite=True)


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
@skip_missing_packages("obstore")
def test_transfer_zarr_local_to_s3(tmpdir: pytest.TempPathFactory) -> None:
    """Test transferring a Zarr file from local to S3.

    Parameters
    ----------
    tmpdir : pytest.TempPathFactory
        Temporary directory factory
    """
    from anemoi.utils.remote.s3 import delete_folder

    fixture = "s3://ml-datasets/aifs-ea-an-oper-0001-mars-20p0-2000-2000-12h-v0-TESTING2.zarr/"
    source = tmpdir.strpath + "/test"
    target = ROOT_S3_WRITE + f"/{uuid.uuid4()}/test.zarr"

    try:

        transfer(fixture, source)
        transfer(source, target)

        with pytest.raises(ValueError, match="already exists"):
            transfer(source, target)

        transfer(source, target, resume=True)
        transfer(source, target, overwrite=True)

    finally:
        delete_folder(target)


def _delete_file_or_directory(path: str) -> None:
    """Delete a file or directory.

    Parameters
    ----------
    path : str
        The path to the file or directory
    """
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    else:
        if os.path.exists(path):
            os.remove(path)


def compare(local1: str, local2: str) -> None:
    """Compare two local files or directories.

    Parameters
    ----------
    local1 : str
        The path to the first file or directory
    local2 : str
        The path to the second file or directory
    """
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
@skip_missing_packages("obstore")
@pytest.mark.parametrize("path", ["directory/", "file"])
def test_transfer_local_to_s3_to_local(path: str) -> None:
    """Test transferring a file or directory from local to S3 and back to local.

    Parameters
    ----------
    path : str
        The path to the file or directory
    """

    from anemoi.utils.remote.s3 import delete
    from anemoi.utils.remote.s3 import list_folder
    from anemoi.utils.remote.s3 import object_exists

    local = LOCAL_TEST_DATA + "/" + path
    remote = ROOT_S3_WRITE + f"/{uuid.uuid4()}/" + path
    local2 = LOCAL_TEST_DATA + "-copy-" + path

    try:

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

    finally:
        delete(remote)

    if remote.endswith("/"):
        assert len(list(list_folder(remote))) == 0
    else:
        assert object_exists(remote) is False


@pytest.mark.skipif(IN_CI, reason="Test requires access to Azurite not available in CI")
@skip_missing_packages("obstore")
@pytest.mark.skipif(not azurite_reachable(), reason=f"Azurite not reachable at endpoint: {AZURITE_ENDPOINT}")
@pytest.mark.parametrize("path", ["directory/", "file"])
def test_transfer_local_to_az_to_local(azurite: None, path: str) -> None:
    """Test transferring a file or directory from local to Azure Blob Storage and back to local.

    Parameters
    ----------
    azurite : None
        Fixture to set up Azurite and anemoi configuration for testing, see conftest.py.
    path : str
        Path to the file or directory to round-trip.

    """
    from anemoi.utils.remote.az import delete
    from anemoi.utils.remote.az import list_folder
    from anemoi.utils.remote.az import object_exists

    local = LOCAL_TEST_DATA + "/" + path
    remote = f"abfs://{AZURITE_CONTAINER}" + f"/{uuid.uuid4()}/" + path
    local2 = LOCAL_TEST_DATA + "-copy-" + path

    try:
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

    finally:
        delete(remote)

    if remote.endswith("/"):
        assert len(list(list_folder(remote))) == 0
    else:
        assert object_exists(remote) is False


@pytest.mark.skipif(IN_CI, reason="Test requires ssh access to localhost")
@pytest.mark.skipif(sys.platform == "darwin", reason="Does not work on MacOS")
@pytest.mark.parametrize("path", ["directory", "file"])
@pytest.mark.parametrize("temporary_target", [True, False])
def test_transfer_local_to_ssh(path: str, temporary_target: bool) -> None:
    """Test transferring a file or directory from local to SSH.

    Parameters
    ----------
    path : str
        The path to the file or directory
    temporary_target : bool
        Whether to use a temporary target
    """
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
