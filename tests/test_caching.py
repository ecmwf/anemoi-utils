# (C) Copyright 2025 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import numpy as np

from anemoi.utils.caching import cached
from anemoi.utils.caching import clean_cache


class Data(dict):
    """Simple class to store data and count the number of calls to the function.

    Attributes
    ----------
    n : int
        The number of calls to the function.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the Data object."""
        super().__init__(*args, **kwargs)
        self.n = 0


def check(f: callable, data: Data) -> None:
    """Check that the function f returns the expected values from the data.

    Parameters
    ----------
    f : callable
        The function to be tested.
    data : Data
        The data to be used for testing.
    """
    """
    The function f is called three times for each value in the data.
    The number of actual calls to the function is checked to make sure the cache is used when it should be.
    """

    for i, x in enumerate(data):
        assert data.n == i

        res = f(x)
        assert type(res) == type(data[x])  # noqa: E721
        assert str(res) == str(data[x])
        assert data.n == i + 1

        res = f(x)
        assert type(res) == type(data[x])  # noqa: E721
        assert str(res) == str(data[x])
        assert data.n == i + 1


global DATA

#########################################
# basic test
#########################################
global values_a
values_a = Data(a=1, b=2)


@cached(collection="test", expires=0)
def func_a(x: str) -> int:
    """Example function to be cached.

    Parameters
    ----------
    x : str
        The key to access the data.

    Returns
    -------
    int
        The value associated with the key.
    """
    global values_a
    values_a.n += 1
    return values_a[x]


def test_cached_basic(*values: str, **kwargs: dict) -> None:
    """Test the cached decorator with basic data types.

    Parameters
    ----------
    values : str
        The values to be tested.
    kwargs : dict
        Additional keyword arguments.
    """
    clean_cache("test")
    check(func_a, values_a)


#########################################
# Test with numpy arrays
#########################################

global values_c
values_c = Data(
    a=dict(A=np.array([1, 2, 3]), B=np.array([4, 5, 6])),
    b=dict(A=np.array([7, 8, 9]), B=np.array([10, 11, 12])),
)


@cached(collection="test", expires=0, encoding="npz")
def func_c(x: str) -> dict:
    """Example function to be cached with numpy arrays.

    Parameters
    ----------
    x : str
        The key to access the data.

    Returns
    -------
    dict
        The value associated with the key.
    """
    global values_c
    values_c.n += 1
    return values_c[x]


def test_cached_npz(*values: str, **kwargs: dict) -> None:
    """Test the cached decorator with numpy arrays.

    Parameters
    ----------
    values : str
        The values to be tested.
    kwargs : dict
        Additional keyword arguments.
    """
    clean_cache("test")
    check(func_c, values_c)


#########################################
# Test with a various types
global values_d
values_d = Data(a="4", b=5.0, c=dict(d=6), e=[7, 8, 9], f=(10, 11, 12))


@cached(collection="test", expires=0)
def func_d(x: str) -> any:
    """Example function to be cached with various data types.

    Parameters
    ----------
    x : str
        The key to access the data.

    Returns
    -------
    any
        The value associated with the key.
    """
    global values_d
    values_d.n += 1
    return values_d[x]


def test_cached_various_types(*values: str, **kwargs: dict) -> None:
    """Test the cached decorator with various data types.

    Parameters
    ----------
    values : str
        The values to be tested.
    kwargs : dict
        Additional keyword arguments.
    """
    clean_cache("test")
    check(func_d, values_d)


#########################################

if __name__ == "__main__":
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
