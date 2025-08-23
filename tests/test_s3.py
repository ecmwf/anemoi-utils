# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os

import pytest

from anemoi.utils.testing import packages_installed

IN_CI = (os.environ.get("GITHUB_WORKFLOW") is not None) or (os.environ.get("IN_CI_HPC") is not None)


ROOT_S3_READ = "s3://ml-tests/test-data/anemoi-utils/pytest/transfer"
ROOT_S3_WRITE = f"s3://ml-tmp/anemoi-utils/pytest/transfer/test-{os.getpid()}"


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
@pytest.mark.skipif(not packages_installed("obstore"), reason="obstore is not installed")
def test_s3_exists() -> None:

    from anemoi.utils.remote.s3 import object_exists

    assert (
        object_exists("s3://ml-datasets/aifs-ea-an-oper-0001-mars-20p0-2000-2000-12h-v0-TESTING2.zarr/.zattrs") is True
    )
    assert object_exists("s3://ml-datasets/does-not-exists") is False


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
@pytest.mark.skipif(not packages_installed("obstore"), reason="obstore is not installed")
def test_s3_list() -> None:

    from anemoi.utils.remote.s3 import list_folder

    count = 0
    size = 0
    for n in list_folder("s3://ml-datasets/aifs-ea-an-oper-0001-mars-20p0-2000-2000-12h-v0-TESTING2.zarr/"):
        count += 1
        size += n["size"]

    assert count == 66
    assert size == 490352


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
@pytest.mark.skipif(not packages_installed("obstore"), reason="obstore is not installed")
def test_s3_info() -> None:

    from anemoi.utils.remote.s3 import object_info

    info = object_info("s3://ml-datasets/aifs-ea-an-oper-0001-mars-20p0-2000-2000-12h-v0-TESTING2.zarr/.zattrs")
    assert info["size"] == 27189
    assert info["path"] == "aifs-ea-an-oper-0001-mars-20p0-2000-2000-12h-v0-TESTING2.zarr/.zattrs"


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
@pytest.mark.skipif(not packages_installed("obstore"), reason="obstore is not installed")
def test_s3_delete_folder() -> None:
    pass


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
@pytest.mark.skipif(not packages_installed("obstore"), reason="obstore is not installed")
def test_s3_delete_object() -> None:
    pass


if __name__ == "__main__":
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
