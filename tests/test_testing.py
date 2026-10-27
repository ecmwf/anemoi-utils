# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import gzip
from pathlib import Path

import pytest

from anemoi.utils import testing
from anemoi.utils.testing import GetTestData
from anemoi.utils.testing import TemporaryDirectoryForTestData


@pytest.fixture
def getter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GetTestData:
    monkeypatch.setattr(testing, "_offline", lambda: False)
    return GetTestData(TemporaryDirectoryForTestData(tmp_path))


def test_broken_download_leaves_no_target(getter: GetTestData, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(url: str, target: str, **kwargs: object) -> None:
        Path(target).write_bytes(b"trunc")
        raise ConnectionError("Broken pipe")

    monkeypatch.setattr(testing, "download", broken)
    with pytest.raises(ConnectionError):
        getter("dir/data.grib")
    assert not Path(getter.temporary_directory_for_test_data("dir/data.grib")).exists()

    # The next call downloads again instead of returning the truncated file.
    monkeypatch.setattr(testing, "download", lambda url, target, **kwargs: Path(target).write_bytes(b"whole"))
    assert Path(getter("dir/data.grib")).read_bytes() == b"whole"


def test_gzipped_download(getter: GetTestData, monkeypatch: pytest.MonkeyPatch) -> None:
    def fetch(url: str, target: str, **kwargs: object) -> None:
        assert url.endswith("data.grib.gz")
        Path(target).write_bytes(gzip.compress(b"whole"))

    monkeypatch.setattr(testing, "download", fetch)
    target = Path(getter("dir/data.grib", gzipped=True))
    assert target.read_bytes() == b"whole"
    assert sorted(p.name for p in target.parent.iterdir()) == ["data.grib"]
