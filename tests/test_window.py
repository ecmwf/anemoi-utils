# (C) Copyright 2026- Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import pytest

from anemoi.utils.window import Window


def test_parse_basic_window() -> None:
    """Test parsing a basic window string with exclusive/inclusive bounds."""
    w = Window("(-3h,+0h]")
    assert w.exclude_before is True
    assert w.exclude_after is False
    assert w.width == 3 * 3600


def test_parse_inclusive_both() -> None:
    """Test parsing a window with inclusive bounds on both sides."""
    w = Window("[-6h,+6h]")
    assert w.exclude_before is False
    assert w.exclude_after is False
    assert w.width == 12 * 3600


def test_parse_exclusive_both() -> None:
    """Test parsing a window with exclusive bounds on both sides."""
    w = Window("(-1d,+1d)")
    assert w.exclude_before is True
    assert w.exclude_after is True
    assert w.width == 2 * 86400


def test_closed_property() -> None:
    """Test the closed property returns correct inclusivity tuple."""
    assert Window("[-1h,+1h]").closed == (True, True)
    assert Window("(-1h,+1h)").closed == (False, False)
    assert Window("(-1h,+1h]").closed == (False, True)
    assert Window("[-1h,+1h)").closed == (True, False)


def test_repr_roundtrip() -> None:
    """Test that repr produces a string that can be re-parsed."""
    for s in ["(-3h,+0h]", "[-6h,+6h]", "(-1h,+1h)", "[-1h,+1h)"]:
        w = Window(s)
        w2 = Window(repr(w))
        assert w.width == w2.width
        assert w.closed == w2.closed


def test_invalid_window_raises() -> None:
    """Test that an invalid window string raises ValueError."""
    with pytest.raises(ValueError, match="invalid window string"):
        Window("invalid")


if __name__ == "__main__":
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
