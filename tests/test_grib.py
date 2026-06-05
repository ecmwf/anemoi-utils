# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Tests for anemoi.utils.grib -- API consistency.

Each test is parametrised over two ParamDB backends:

- **local**: our own test YAML fixture -- always available.
- **bundled**: pymetkit's shipped parameter_metadata.yaml.
  Currently xfail because the YAML is not packaged with the dev install.
  Will start passing (and enforcing) once pymetkit ships it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pymetkit import ParamDB

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_YAML = Path(__file__).parent / "parameter_metadata_test.yaml"


@pytest.fixture(scope="session")
def _local_paramdb():
    return ParamDB(mode="offline", yaml_path=FIXTURE_YAML.resolve())


@pytest.fixture(scope="session")
def _offline_paramdb():
    return ParamDB(mode="offline")


@pytest.fixture(params=["local", "bundled"])
def grib(request, monkeypatch, _local_paramdb, _offline_paramdb):
    """Swap anemoi.utils.grib.PARAMDB to the requested backend.

    'local' reuses a session-scoped ParamDB pointing at our test YAML.
    'bundled' constructs one from pymetkit's default YAML lookup (which may
    not exist, in which case the test xfails on FileNotFoundError).
    """
    import anemoi.utils.grib as grib_mod

    db = _local_paramdb if request.param == "local" else _offline_paramdb
    monkeypatch.setattr(grib_mod, "PARAMDB", db)
    return grib_mod


# ---------------------------------------------------------------------------
# shortname_to_paramid
# ---------------------------------------------------------------------------


class TestShortNameToParamId:
    @pytest.mark.parametrize(
        "shortname,expected_id",
        [
            ("2t", 167),
            ("tp", 228),
            ("sp", 134),
            ("msl", 151),
            ("ci", 31),
        ],
    )
    def test_known_params(self, grib, shortname, expected_id):
        result = grib.shortname_to_paramid(shortname)
        assert result == expected_id
        assert isinstance(result, int)

    def test_unknown_raises_key_error(self, grib):
        with pytest.raises(KeyError):
            grib.shortname_to_paramid("nonexistent_xyz")


# ---------------------------------------------------------------------------
# paramid_to_shortname
# ---------------------------------------------------------------------------


class TestParamIdToShortName:
    @pytest.mark.parametrize(
        "paramid,expected_name",
        [
            (167, "2t"),
            (228, "tp"),
            (134, "sp"),
            (151, "msl"),
            (31, "ci"),
        ],
    )
    def test_known_params(self, grib, paramid, expected_name):
        result = grib.paramid_to_shortname(paramid)
        assert result == expected_name
        assert isinstance(result, str)

    def test_unknown_raises_key_error(self, grib):
        with pytest.raises(KeyError):
            grib.paramid_to_shortname(9999999)


# ---------------------------------------------------------------------------
# Roundtrip consistency
# ---------------------------------------------------------------------------


class TestRoundtripConsistency:
    @pytest.mark.parametrize("shortname", ["2t", "tp", "sp", "msl", "10u", "10v"])
    def test_shortname_roundtrip(self, grib, shortname):
        paramid = grib.shortname_to_paramid(shortname)
        assert grib.paramid_to_shortname(paramid) == shortname

    @pytest.mark.parametrize("paramid", [167, 228, 134, 151, 165, 166])
    def test_paramid_roundtrip(self, grib, paramid):
        shortname = grib.paramid_to_shortname(paramid)
        assert grib.shortname_to_paramid(shortname) == paramid


# ---------------------------------------------------------------------------
# units
# ---------------------------------------------------------------------------


class TestUnits:
    @pytest.mark.parametrize(
        "param,expected_unit",
        [
            ("2t", "K"),
            ("tp", "m"),
            ("sp", "Pa"),
            ("10u", "m s**-1"),
            (167, "K"),
            (228, "m"),
        ],
    )
    def test_known_units(self, grib, param, expected_unit):
        result = grib.units(param)
        assert result == expected_unit
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# must_be_positive
# ---------------------------------------------------------------------------


class TestMustBePositive:
    @pytest.mark.parametrize(
        "param,expected",
        [
            ("tp", True),  # units: m
            ("crwc", True),  # units: kg kg**-1
            ("sf", True),  # units: m of water equivalent
            ("2t", False),  # units: K
            ("sp", False),  # units: Pa
            ("10u", False),  # units: m s**-1
            ("cape", False),  # units: J kg**-1
        ],
    )
    def test_positive_classification(self, grib, param, expected):
        result = grib.must_be_positive(param)
        assert result is expected
        assert isinstance(result, bool)

    def test_accepts_paramid(self, grib):
        assert grib.must_be_positive(228) is True  # tp, units: m
        assert grib.must_be_positive(167) is False  # 2t, units: K
