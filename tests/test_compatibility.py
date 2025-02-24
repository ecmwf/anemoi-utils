# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import pytest

from anemoi.utils.compatibility import aliases


def test_aliases() -> None:
    """Test the aliases decorator for function argument aliases."""

    @aliases(a="b", c=["d", "e"])
    def func(a, c):
        return a, c

    assert func(a=1, c=2) == (1, 2)
    assert func(a=1, d=2) == (1, 2)
    assert func(b=1, d=2) == (1, 2)


def test_duplicate_values() -> None:
    """Test the aliases decorator for handling duplicate values."""

    @aliases(a="b", c=["d", "e"])
    def func(a, c):
        return a, c

    with pytest.raises(ValueError):
        func(a=1, b=2)
