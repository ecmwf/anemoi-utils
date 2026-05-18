# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from anemoi.utils.config import DotDict
from anemoi.utils.config import _merge_dicts
from anemoi.utils.config import _set_defaults
from anemoi.utils.config import temporary_config
from anemoi.utils.grib import paramid_to_shortname
from anemoi.utils.grib import shortname_to_paramid


def test_dotdict() -> None:
    """Test the DotDict class for nested dictionary access and assignment.

    Tests:
        - Accessing nested dictionary values.
        - Assigning new values to existing keys.
        - Adding new nested dictionaries.
        - Accessing and assigning values in nested lists.
    """
    d = DotDict(a=1, b=2, c=dict(d=3, e=4), e=[1, dict(a=3), 3])
    assert d.a == 1
    assert d.b == 2
    assert d.c.d == 3
    assert d.c.e == 4

    d.a = 10
    assert d.a == 10

    d.d = dict(f=5)
    assert d.d.f == 5

    d.d.x = 6
    assert d.d.x == 6

    assert d.e[1].a == 3


def test_add_nested_dict_via_setitem():
    """Test that assigning a nested dict via item access results in recursive DotDict conversion."""

    d = DotDict(a=1)
    d["b"] = {
        "c": "d",
    }
    assert d.b.c == "d"


def test_adding_list_of_dicts_via_setitem():
    d = DotDict(a=1)
    d["b"] = [
        {
            "c": "d",
        },
        {"e": "f"},
    ]
    assert d.b[0].c == "d"
    assert d.b[1].e == "f"


def test_adding_list_of_dicts_via_setattr():
    d = DotDict(a=1)
    d.b = [
        {
            "c": "d",
        },
        {"e": "f"},
    ]
    assert d.b[0].c == "d"
    assert d.b[1].e == "f"


def test_merge_dicts() -> None:
    """Test the _merge_dicts function for merging nested dictionaries.

    Tests:
        - Merging two dictionaries with overlapping keys.
        - Ensuring nested dictionaries are merged correctly.
    """
    a = dict(a=1, b=2, c=dict(d=3, e=4))
    b = dict(a=10, c=dict(a=30, e=40), d=9)
    _merge_dicts(a, b)
    assert a == {"a": 10, "b": 2, "c": {"d": 3, "e": 40, "a": 30}, "d": 9}


def test_set_defaults() -> None:
    """Test the _set_defaults function for setting default values in nested dictionaries.

    Tests:
        - Setting default values without overwriting existing ones.
        - Ensuring nested dictionaries are handled correctly.
    """
    a = dict(a=1, b=2, c=dict(d=3, e=4))
    b = dict(a=10, c=dict(a=30, e=40), d=9)
    _set_defaults(a, b)
    assert a == {"a": 1, "b": 2, "c": {"d": 3, "e": 4, "a": 30}, "d": 9}


def test_grib() -> None:
    """Test the GRIB utility functions.

    Tests:
        - Converting short names to parameter IDs.
        - Converting parameter IDs to short names.
    """
    assert shortname_to_paramid("2t") == 167
    assert paramid_to_shortname(167) == "2t"


def test_config_runtime_resolution() -> None:
    """Test that LazyConfig resolves config values at runtime, not at import time.

    The grib module's CONFIG object uses properties that read from
    load_config() on every access. This ensures that temporary_config
    overrides are picked up dynamically without reimporting the module.

    Tests:
        - default_origin reflects runtime config changes
        - local_cache reflects runtime config changes
        - cache_length reflects runtime config changes
        - values revert after the temporary_config context exits
    """
    from anemoi.utils.grib import GRIB_CONFIG

    # Capture the defaults before any override
    original_origin = GRIB_CONFIG.default_origin
    original_local_cache = GRIB_CONFIG.local_cache
    original_cache_length = GRIB_CONFIG.cache_length

    # Override paramdb config at runtime
    with temporary_config(
        {
            "paramdb": {
                "default_origin": "test_origin",
                "local_cache": "/tmp/test.json",
                "cache_length": 99,
            }
        }
    ):
        assert (
            GRIB_CONFIG.default_origin == "test_origin"
        ), f"Expected 'test_origin', got '{GRIB_CONFIG.default_origin}'"
        assert (
            GRIB_CONFIG.local_cache == "/tmp/test.json"
        ), f"Expected '/tmp/test.json', got '{GRIB_CONFIG.local_cache}'"
        # cache_length is multiplied by 24*3600 in the property
        assert GRIB_CONFIG.cache_length == 99 * 24 * 3600, f"Expected {99 * 24 * 3600}, got {GRIB_CONFIG.cache_length}"

    # After exiting the context, values should revert to defaults
    assert (
        GRIB_CONFIG.default_origin == original_origin
    ), f"Expected '{original_origin}' after context exit, got '{GRIB_CONFIG.default_origin}'"
    assert (
        GRIB_CONFIG.local_cache == original_local_cache
    ), f"Expected '{original_local_cache}' after context exit, got '{GRIB_CONFIG.local_cache}'"
    assert (
        GRIB_CONFIG.cache_length == original_cache_length
    ), f"Expected '{original_cache_length}' after context exit, got '{GRIB_CONFIG.cache_length}'"


if __name__ == "__main__":
    """Run all test functions."""
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
