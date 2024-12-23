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


def test_dotdict():
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


def test_merge_dicts():
    a = dict(a=1, b=2, c=dict(d=3, e=4))
    b = dict(a=10, c=dict(a=30, e=40), d=9)
    _merge_dicts(a, b)
    assert a == {"a": 10, "b": 2, "c": {"d": 3, "e": 40, "a": 30}, "d": 9}


def test_set_defaults():
    a = dict(a=1, b=2, c=dict(d=3, e=4))
    b = dict(a=10, c=dict(a=30, e=40), d=9)
    _set_defaults(a, b)
    assert a == {"a": 1, "b": 2, "c": {"d": 3, "e": 4, "a": 30}, "d": 9}


def test_grib():
    assert shortname_to_paramid("2t") == 167
    assert paramid_to_shortname(167) == "2t"


if __name__ == "__main__":
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
