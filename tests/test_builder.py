# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import functools

import pytest

from anemoi.utils.builder import Builder
from anemoi.utils.builder import BuilderError
from anemoi.utils.builder import as_dict
from anemoi.utils.builder import build
from anemoi.utils.builder import build_all
from anemoi.utils.builder import locate


class Widget:
    def __init__(self, a, b=2, child=None):
        self.a = a
        self.b = b
        self.child = child


class Child:
    def __init__(self, name="x"):
        self.name = name


def test_locate_module_attribute():
    assert locate("math.sqrt")(4) == 2.0


def test_locate_nested_attribute():
    assert locate("tests.test_builder.Widget") is Widget


def test_locate_bad_path_raises():
    with pytest.raises(BuilderError):
        locate("nonexistent.module.thing")


def test_build_simple_target():
    obj = build({"_target_": "tests.test_builder.Widget", "a": 1})
    assert isinstance(obj, Widget)
    assert obj.a == 1 and obj.b == 2


def test_runtime_kwargs_override_spec():
    obj = build({"_target_": "tests.test_builder.Widget", "a": 1, "b": 3}, b=9)
    assert obj.b == 9


def test_positional_runtime_args():
    obj = build({"_target_": "tests.test_builder.Widget"}, 7)
    assert obj.a == 7


def test_partial_returns_callable():
    factory = build({"_target_": "tests.test_builder.Widget", "_partial_": True, "b": 5})
    assert isinstance(factory, functools.partial)
    obj = factory(a=1)
    assert obj.a == 1 and obj.b == 5


def test_recursive_builds_nested_target():
    obj = build(
        {
            "_target_": "tests.test_builder.Widget",
            "a": 1,
            "child": {"_target_": "tests.test_builder.Child", "name": "deep"},
        }
    )
    assert isinstance(obj.child, Child)
    assert obj.child.name == "deep"


def test_non_recursive_passes_nested_spec_through():
    child_spec = {"_target_": "tests.test_builder.Child", "name": "deep"}
    obj = build(
        {
            "_target_": "tests.test_builder.Widget",
            "a": 1,
            "child": child_spec,
            "_recursive_": False,
        }
    )
    assert obj.child == child_spec


def test_non_target_mapping_returned_as_is():
    spec = {"a": 1, "b": 2}
    assert build(spec) == spec


def test_recursive_preserves_pure_data_container_identity():
    # A pure-data nested mapping (no _target_) is passed through unchanged.
    data = {"x": 1, "y": [1, 2, 3]}
    obj = build({"_target_": "tests.test_builder.Widget", "a": 1, "child": data})
    assert obj.child is data


def test_builder_get_dotted():
    b = Builder({"model": {"num_channels": 512}})
    assert b.get("model.num_channels") == 512
    assert b.get("model.missing", "d") == "d"


def test_build_error_wraps_target_failure():
    with pytest.raises(BuilderError):
        build({"_target_": "tests.test_builder.Widget"})  # missing required 'a'


def test_build_all_mapping_injects_kwargs():
    objs = build_all(
        {
            "one": {"_target_": "tests.test_builder.Widget", "a": 1},
            "two": {"_target_": "tests.test_builder.Widget", "a": 2},
        },
        b=7,
    )
    assert set(objs) == {"one", "two"}
    assert objs["one"].a == 1 and objs["one"].b == 7
    assert objs["two"].a == 2 and objs["two"].b == 7


def test_build_all_sequence_preserves_order():
    objs = build_all(
        [
            {"_target_": "tests.test_builder.Widget", "a": 1},
            {"_target_": "tests.test_builder.Widget", "a": 2},
        ]
    )
    assert [o.a for o in objs] == [1, 2]


def test_build_all_rejects_scalar():
    with pytest.raises(BuilderError):
        build_all("not-a-collection")


def test_as_dict_passes_plain_dict_through():
    d = {"a": 1, "b": {"c": 2}}
    assert as_dict(d) is d


def test_as_dict_materialises_omegaconf():
    OmegaConf = pytest.importorskip("omegaconf").OmegaConf
    cfg = OmegaConf.create({"a": 1, "b": "${a}"})
    out = as_dict(cfg)
    assert isinstance(out, dict) and out == {"a": 1, "b": 1}
