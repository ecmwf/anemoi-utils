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

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from pymetkit import ParamDB

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_YAML = Path(__file__).parent / "parameter_metadata_test.yaml"

_bundled_xfail = pytest.param(
    "bundled",
    marks=pytest.mark.xfail(
        raises=FileNotFoundError,
        reason="pymetkit bundled YAML not installed in this environment",
        strict=False,
    ),
)


@pytest.fixture(params=["local", _bundled_xfail])
def grib(request, monkeypatch):
    """Import anemoi.utils.grib and swap PARAMDB to the requested backend.

    For 'local', the module is imported with settings pointing at our test
    YAML. For 'bundled', PARAMDB is replaced with a ParamDB using pymetkit's
    default YAML lookup (which may not exist).
    """
    from anemoi.utils.settings import AnemoiSettings

    yaml_path = FIXTURE_YAML.resolve()
    settings = AnemoiSettings()
    settings.paramdb.local_data = yaml_path

    # Ensure a clean import of the grib module with patched settings
    cached = sys.modules.pop("anemoi.utils.grib", None)
    try:
        with patch("anemoi.utils.settings.AnemoiSettings", return_value=settings):
            import anemoi.utils.grib as grib_mod

        if request.param == "bundled":
            bundled = ParamDB(mode="offline")
            monkeypatch.setattr(grib_mod, "PARAMDB", bundled)

        yield grib_mod
    finally:
        sys.modules.pop("anemoi.utils.grib", None)
        if cached is not None:
            sys.modules["anemoi.utils.grib"] = cached


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
