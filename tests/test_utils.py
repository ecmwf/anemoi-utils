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


if __name__ == "__main__":
    """Run all test functions."""
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
