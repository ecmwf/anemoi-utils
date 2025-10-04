# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from anemoi.utils.config import DotDict
from anemoi.utils.settings import _merge_dicts
from anemoi.utils.settings import _set_defaults


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
    """Test that assigning a list of dicts via item access results in recursive DotDict conversion.

    Tests
    -----
    - Assigning a list of dicts to a DotDict key.
    - Ensuring each dict in the list is converted to DotDict.
    """
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
    """Test that assigning a list of dicts via attribute access results in recursive DotDict conversion.

    Tests
    -----
    - Assigning a list of dicts to a DotDict attribute.
    - Ensuring each dict in the list is converted to DotDict.
    """
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


def test_interpolation() -> None:
    """Test interpolation in DotDict using OmegaConf-like syntax.

    Tests
    -----
    - Interpolating values from other keys using nested references.
    """
    # From omegaconf documentation

    d = DotDict(
        {
            "plans": {
                "A": "plan A",
                "B": "plan B",
            },
            "selected_plan": "A",
            "plan": "${plans[${selected_plan}]}",
        }
    )

    assert d.to_dict() == {"plan": "plan A", "plans": {"A": "plan A", "B": "plan B"}, "selected_plan": "A"}


def test_cli_arguments() -> None:
    """Test that DotDict correctly applies CLI arguments to override values.

    Tests
    -----
    - Overriding top-level and nested values using CLI arguments.
    """
    d = DotDict(
        {
            "a": 1,
            "b": 2,
            "c": {
                "d": 3,
                "e": 4,
            },
        },
        cli_arguments=["a=10", "c.d=30"],
    )

    assert d.a == 10
    assert d.b == 2
    assert d.c.d == 30
    assert d.c.e == 4


def test_non_primitive_types() -> None:
    """Test that DotDict can handle non-primitive types like datetime.

    Tests
    -----
    - Assigning and accessing datetime objects in DotDict.
    """
    from datetime import datetime

    now = datetime.now()
    d = DotDict(a=now)
    assert d.a == now

    d.b = {"time": now}
    assert d.b.time == now

    d = DotDict()
    d.c = [1, 2, {"time": now}]
    assert d.c[2].time == now


if __name__ == "__main__":
    """Run all test functions."""
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
