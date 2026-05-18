# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Tests for grib.py — GRIB parameter lookup utilities.

Covers the filtering/disambiguation logic added in the advanced-shortname-filtering
feature, including origin-based filtering and default origin fallback.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from anemoi.utils.config import temporary_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(json_data, status_code=200):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


# Sample API payloads -------------------------------------------------------

PARAM_2T_ECMF = {
    "id": 167,
    "shortname": "2t",
    "name": "2 metre temperature",
    "unit_id": 1,
    "access_ids": ["dissemination"],
}

PARAM_2T_OTHER = {
    "id": 500167,
    "shortname": "2t",
    "name": "2 metre temperature (other centre)",
    "unit_id": 1,
    "access_ids": [],
}

PARAM_AMBIGUOUS_A = {
    "id": 200,
    "shortname": "xx",
    "name": "Ambiguous param A",
    "unit_id": 1,
    "access_ids": [],
}

PARAM_AMBIGUOUS_B = {
    "id": 300,
    "shortname": "xx",
    "name": "Ambiguous param B",
    "unit_id": 1,
    "access_ids": [],
}

ORIGIN_ECMF = {
    "id": 98,
    "abbreviation": "ecmf",
    "name": "European Centre for Medium-Range Weather Forecasts",
}
ORIGIN_DESTINE = {
    "id": -60,
    "abbreviation": "destine",
    "name": "Destination Earth Local parameter definitions",
}

ALL_ORIGINS = [ORIGIN_ECMF, ORIGIN_DESTINE]


# ---------------------------------------------------------------------------
# Fixtures — patch caching so every call goes straight through
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _bypass_cache(monkeypatch):
    """Replace the @cached decorator with a no-op so tests hit the mocked API."""
    import anemoi.utils.caching as caching_mod

    def _noop_cached(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    monkeypatch.setattr(caching_mod, "cached", _noop_cached)

    # Re-import the module so the patched decorator is applied
    import importlib

    import anemoi.utils.grib as grib_mod

    importlib.reload(grib_mod)
    yield
    # Reload again to restore original state for other test modules
    importlib.reload(grib_mod)


def _grib():
    """Import the reloaded grib module."""
    import anemoi.utils.grib as grib_mod

    return grib_mod


# ---------------------------------------------------------------------------
# Basic lookup tests
# ---------------------------------------------------------------------------


class TestShortNameToParamId:
    """Tests for shortname_to_paramid."""

    @patch("anemoi.utils.grib.requests.get")
    def test_single_result(self, mock_get):
        """A unique match returns the parameter id directly."""
        mock_get.return_value = _mock_response([PARAM_2T_ECMF])

        grib = _grib()
        assert grib.shortname_to_paramid("2t") == 167

    @patch("anemoi.utils.grib.requests.get")
    def test_no_result_raises_key_error(self, mock_get):
        """No matches should raise KeyError."""
        mock_get.return_value = _mock_response([])

        grib = _grib()
        with pytest.raises(KeyError):
            grib.shortname_to_paramid("nonexistent")


class TestParamIdToShortName:
    """Tests for paramid_to_shortname."""

    @patch("anemoi.utils.grib.requests.get")
    def test_single_result(self, mock_get):
        """A unique match returns the shortname."""
        mock_get.return_value = _mock_response([PARAM_2T_ECMF])

        grib = _grib()
        assert grib.paramid_to_shortname(167) == "2t"


# ---------------------------------------------------------------------------
# Disambiguation tests
# ---------------------------------------------------------------------------


class TestDisambiguationByDissemination:
    """When multiple results exist, a single 'dissemination' entry wins."""

    @patch("anemoi.utils.grib.requests.get")
    def test_dissemination_filter_selects_correct_entry(self, mock_get):
        """If exactly one result has 'dissemination' access, it is returned."""
        # The correct entry (PARAM_2T_ECMF) is second in the response list
        mock_get.return_value = _mock_response([PARAM_2T_OTHER, PARAM_2T_ECMF])

        grib = _grib()
        result = grib.shortname_to_paramid("2t")
        assert result == 167, (
            "Should pick the entry with 'dissemination' access (id=167), " "not the first entry (id=500167)"
        )


class TestDisambiguationByDefaultOrigin:
    """When dissemination doesn't resolve ambiguity, default_origin is applied."""

    @patch("anemoi.utils.grib.requests.get")
    def test_default_origin_applied_when_ambiguous(self, mock_get):
        """Two results, neither with dissemination → falls back to default_origin filter.

        The second API call (with origin filter) returns the correct single match.
        """

        # First call: ambiguous, two results without dissemination
        # Second call (with origin): returns only the correct one
        # Third call: origin lookup
        def side_effect(url, **kwargs):
            if "origin/" in url:
                return _mock_response(ALL_ORIGINS)
            if "origin=" in url:
                # Filtered call returns the correct entry only
                return _mock_response([PARAM_AMBIGUOUS_A])
            # Unfiltered call returns ambiguous results
            return _mock_response([PARAM_AMBIGUOUS_B, PARAM_AMBIGUOUS_A])

        mock_get.side_effect = side_effect

        grib = _grib()
        result = grib.shortname_to_paramid("xx")
        # The default_origin filter resolves to PARAM_AMBIGUOUS_A (id=200)
        assert result == 200

    @patch("anemoi.utils.grib.requests.get")
    def test_default_origin_fallback_to_sorted_first(self, mock_get):
        """If default_origin also fails (KeyError), returns sorted first result."""

        def side_effect(url, **kwargs):
            if "origin/" in url:
                return _mock_response(ALL_ORIGINS)
            if "origin=" in url:
                # Origin filter yields nothing
                return _mock_response([])
            # Unfiltered: ambiguous
            return _mock_response([PARAM_AMBIGUOUS_B, PARAM_AMBIGUOUS_A])

        mock_get.side_effect = side_effect

        grib = _grib()
        # Should fall back to sorted-first → id 200 (PARAM_AMBIGUOUS_A)
        result = grib.shortname_to_paramid("xx")
        assert result == 200, "Should return the entry with the lowest id after sorting"


# ---------------------------------------------------------------------------
# Explicit filter tests
# ---------------------------------------------------------------------------


class TestExplicitOriginFilter:
    """Passing origin= explicitly should change the returned parameter."""

    @patch("anemoi.utils.grib.requests.get")
    def test_origin_filter_changes_returned_key(self, mock_get):
        """Filtering by origin should return the correct entry even when it is
        the second item in the unfiltered response.

        This verifies that filtering by origin (and by extension the default
        origin) correctly selects a different entry than a naive 'first result'
        approach would.
        """

        def side_effect(url, **kwargs):
            if "origin/" in url:
                return _mock_response(ALL_ORIGINS)
            if "origin=98" in url:
                # When filtered by ecmf origin (id=98), only the ECMF entry
                return _mock_response([PARAM_2T_ECMF])
            if "origin=-60" in url:
                # When filtered by destine origin (id=-60), only the other entry
                return _mock_response([PARAM_2T_OTHER])
            # Unfiltered
            return _mock_response([PARAM_2T_OTHER, PARAM_2T_ECMF])

        mock_get.side_effect = side_effect

        grib = _grib()

        # Without filter the correct entry (167) is the SECOND in the response.
        # The dissemination filter would pick it, but with an explicit origin
        # the API is called with origin= directly and returns only that entry.
        result_ecmf = grib.shortname_to_paramid("2t")
        assert (
            result_ecmf == 167
        ), "Filtering by nothing should return the ECMF entry with id 167, as it is set by default"

        result_ecmf = grib.shortname_to_paramid("2t", origin="ecmf")
        assert result_ecmf == 167

        result_destine = grib.shortname_to_paramid("2t", origin="destine")
        assert result_destine == 500167

    @patch("anemoi.utils.grib.requests.get")
    def test_origin_filter_not_reapplied_when_already_provided(self, mock_get):
        """If the caller already passes origin=, the default_origin fallback
        should NOT be applied on top of it.
        """

        def side_effect(url, **kwargs):
            if "origin/" in url:
                return _mock_response(ALL_ORIGINS)
            # Even with origin filter, still ambiguous (edge case)
            return _mock_response([PARAM_AMBIGUOUS_B, PARAM_AMBIGUOUS_A])

        mock_get.side_effect = side_effect

        grib = _grib()
        result = grib.shortname_to_paramid("xx", origin="destine")
        # Should NOT recurse with default_origin because origin was already
        # provided. Falls through to sorted first → id 200.
        assert result == 200

    @patch("anemoi.utils.grib.requests.get")
    def test_paramid_to_shortname_with_origin_filter(self, mock_get):
        """paramid_to_shortname also forwards filters correctly."""

        def side_effect(url, **kwargs):
            if "origin/" in url:
                return _mock_response(ALL_ORIGINS)
            if "origin=" in url:
                return _mock_response([PARAM_2T_ECMF])
            return _mock_response([PARAM_2T_OTHER, PARAM_2T_ECMF])

        mock_get.side_effect = side_effect

        grib = _grib()
        result = grib.paramid_to_shortname(167, origin="ecmf")
        assert result == "2t"


# ---------------------------------------------------------------------------
# _search_origin tests
# ---------------------------------------------------------------------------


class TestSearchOrigin:
    """Tests for the _search_origin helper."""

    @patch("anemoi.utils.grib.requests.get")
    def test_known_origin(self, mock_get):
        mock_get.return_value = _mock_response(ALL_ORIGINS)

        grib = _grib()
        result = grib.origin("ecmf")
        assert result["id"] == 98
        assert result["abbreviation"] == "ecmf"

    @patch("anemoi.utils.grib.requests.get")
    def test_unknown_origin_raises_key_error(self, mock_get):
        mock_get.return_value = _mock_response(ALL_ORIGINS)

        grib = _grib()
        with pytest.raises(KeyError):
            grib.origin("zzzz")


# ---------------------------------------------------------------------------
# units / must_be_positive tests
# ---------------------------------------------------------------------------


class TestUnits:
    """Tests for the units() and must_be_positive() helpers."""

    @patch("anemoi.utils.grib.requests.get")
    def test_units_returns_correct_string(self, mock_get):
        unit_data = [{"id": 1, "name": "K"}, {"id": 2, "name": "m"}]

        def side_effect(url, **kwargs):
            if "unit/" in url:
                return _mock_response(unit_data)
            return _mock_response([PARAM_2T_ECMF])

        mock_get.side_effect = side_effect

        grib = _grib()
        assert grib.units("2t") == "K"

    @patch("anemoi.utils.grib.requests.get")
    def test_must_be_positive(self, mock_get):
        unit_data = [{"id": 1, "name": "K"}, {"id": 2, "name": "m"}]
        param_tp = {**PARAM_2T_ECMF, "id": 228, "shortname": "tp", "unit_id": 2}

        def side_effect(url, **kwargs):
            if "unit/" in url:
                return _mock_response(unit_data)
            return _mock_response([param_tp])

        mock_get.side_effect = side_effect

        grib = _grib()
        assert grib.must_be_positive("tp") is True

    @patch("anemoi.utils.grib.requests.get")
    def test_must_be_positive_false(self, mock_get):
        unit_data = [{"id": 1, "name": "K"}]

        def side_effect(url, **kwargs):
            if "unit/" in url:
                return _mock_response(unit_data)
            return _mock_response([PARAM_2T_ECMF])

        mock_get.side_effect = side_effect

        grib = _grib()
        assert grib.must_be_positive("2t") is False


# ---------------------------------------------------------------------------
# URL construction tests
# ---------------------------------------------------------------------------


class TestUrlConstruction:
    """Verify that filter kwargs are appended to the API URL."""

    @patch("anemoi.utils.grib.requests.get")
    def test_filters_appended_to_url(self, mock_get):
        mock_get.return_value = _mock_response([PARAM_2T_ECMF])

        grib = _grib()
        grib.shortname_to_paramid("2t", encoding=1, table=128)

        call_url = mock_get.call_args[0][0]
        assert "encoding=1" in call_url
        assert "table=128" in call_url

    @patch("anemoi.utils.grib.requests.get")
    def test_origin_string_resolved_to_id_in_url(self, mock_get):
        """When origin is a string, it should be resolved to a numeric id
        via _search_origin before being appended to the URL.
        """

        def side_effect(url, **kwargs):
            if "origin/" in url:
                return _mock_response(ALL_ORIGINS)
            return _mock_response([PARAM_2T_ECMF])

        mock_get.side_effect = side_effect

        grib = _grib()
        grib.shortname_to_paramid("2t", origin="ecmf")

        # Find the param search call (not the origin lookup)
        param_calls = [c for c in mock_get.call_args_list if "param/" in str(c)]
        assert len(param_calls) >= 1
        param_url = param_calls[0][0][0]
        assert "origin=98" in param_url, f"Expected origin to be resolved to numeric id 98, got URL: {param_url}"


# ---------------------------------------------------------------------------
# Local cache tests
# ---------------------------------------------------------------------------

# Minimal mock data modelled after parameters.json structure
LOCAL_CACHE_DATA = [
    {
        "id": 1,
        "name": "Stream function",
        "shortname": "strf",
        "unit_id": 1,
        "encoding_ids": ["grib1", "grib2"],
        "access_ids": ["dissemination"],
        "published": True,
        "pending": False,
        "retired": False,
    },
    {
        "id": 2,
        "name": "Velocity potential",
        "shortname": "vp",
        "unit_id": 1,
        "encoding_ids": ["grib1", "grib2"],
        "access_ids": ["dissemination"],
        "published": True,
        "pending": False,
        "retired": False,
    },
    {
        "id": 10,
        "name": "Wind speed",
        "shortname": "ws",
        "unit_id": 5,
        "encoding_ids": ["grib1", "grib2"],
        "access_ids": ["dissemination"],
        "published": True,
        "pending": False,
        "retired": False,
    },
    {
        "id": 31,
        "name": "Sea ice area fraction",
        "shortname": "ci",
        "unit_id": 3,
        "encoding_ids": ["grib1", "grib2"],
        "access_ids": ["dissemination"],
        "published": True,
        "pending": False,
        "retired": False,
    },
    {
        "id": 34,
        "name": "Sea surface temperature",
        "shortname": "sst",
        "unit_id": 2,
        "encoding_ids": ["grib1", "grib2"],
        "access_ids": ["dissemination"],
        "published": True,
        "pending": False,
        "retired": False,
    },
    {
        "id": 54,
        "name": "Pressure",
        "shortname": "pres",
        "unit_id": 16,
        "encoding_ids": ["grib1", "grib2"],
        "access_ids": ["dissemination"],
        "published": True,
        "pending": False,
        "retired": False,
    },
    {
        "id": 59,
        "name": "Convective available potential energy",
        "shortname": "cape",
        "unit_id": 17,
        "encoding_ids": ["grib1", "grib2"],
        "access_ids": [],
        "published": True,
        "pending": False,
        "retired": False,
    },
]


@pytest.fixture()
def local_cache_file(tmp_path):
    """Write LOCAL_CACHE_DATA to a temporary JSON file and return its path."""
    cache_file = tmp_path / "parameters.json"
    cache_file.write_text(json.dumps(LOCAL_CACHE_DATA))
    return str(cache_file)


class TestLocalCacheSearch:
    """Tests for _local_search_param and the CONFIG.local_cache routing in _search_param."""

    def test_local_search_param_returns_single_match(self, local_cache_file):
        """_local_search_param returns a one-element list for a known shortname."""
        grib = _grib()
        with temporary_config({"paramdb": {"local_cache": local_cache_file}}):
            results = grib._local_search_param("sst")
            assert len(results) == 1
            assert results[0]["shortname"] == "sst"
            assert results[0]["id"] == 34

    def test_local_search_param_raises_on_missing(self, local_cache_file):
        """_local_search_param raises KeyError for an unknown shortname."""
        grib = _grib()
        with temporary_config({"paramdb": {"local_cache": local_cache_file}}):
            with pytest.raises(KeyError, match="not found in local cache"):
                grib._local_search_param("nonexistent_param_xyz")

    @patch("anemoi.utils.grib.requests.get")
    def test_search_param_local_cache_no_network(self, mock_get, local_cache_file):
        """Verify requests.get is never called when local_cache is configured."""
        grib = _grib()
        with temporary_config({"paramdb": {"local_cache": local_cache_file}}):
            result = grib._search_param("ws")
            mock_get.assert_not_called()
            assert result["shortname"] == "ws"
            assert result["id"] == 10

    @patch("anemoi.utils.grib.requests.get")
    def test_shortname_to_paramid_via_local_cache(self, mock_get, local_cache_file):
        """End-to-end: shortname_to_paramid works with the local cache."""
        grib = _grib()
        with temporary_config({"paramdb": {"local_cache": local_cache_file}}):
            assert grib.shortname_to_paramid("ci") == 31
            assert grib.shortname_to_paramid("sst") == 34
            assert grib.shortname_to_paramid("pres") == 54
            mock_get.assert_not_called()

    @patch("anemoi.utils.grib.requests.get")
    def test_paramid_to_shortname_via_local_cache(self, mock_get, local_cache_file):
        """_search_param finds entries via local cache for reverse lookups."""
        grib = _grib()
        with temporary_config({"paramdb": {"local_cache": local_cache_file}}):
            result = grib._search_param("sst")
            assert result["shortname"] == "sst"
            mock_get.assert_not_called()

    @patch("anemoi.utils.grib.warnings.warn")
    def test_local_cache_filters_ignored_with_warning(self, mock_warning, local_cache_file):
        """When local_cache is set, passing filters emits a warning."""
        grib = _grib()
        with temporary_config({"paramdb": {"local_cache": local_cache_file}}):
            result = grib._search_param("sst", origin=98)
            mock_warning.assert_called()
            warning_msg = mock_warning.call_args[0][0]
            assert "ignored" in warning_msg.lower() or "Filters" in warning_msg
            assert result["id"] == 34

    def test_local_search_multiple_params(self, local_cache_file):
        """Verify several known parameters from the mock cache are found."""
        grib = _grib()
        with temporary_config({"paramdb": {"local_cache": local_cache_file}}):
            expected = {
                "strf": 1,
                "vp": 2,
                "ws": 10,
                "cape": 59,
            }
            for shortname, expected_id in expected.items():
                results = grib._local_search_param(shortname)
                assert len(results) == 1
                assert (
                    results[0]["id"] == expected_id
                ), f"Expected {shortname} -> id={expected_id}, got {results[0]['id']}"
