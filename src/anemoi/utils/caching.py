# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import hashlib
import json
import os
import time
from threading import Lock
from typing import Any
from typing import Callable
from typing import Optional

import numpy as np

LOCK = Lock()
CACHE = {}


def _get_cache_path(collection: str) -> str:
    """Get the cache path for a collection.

    Parameters
    ----------
    collection : str
        The name of the collection

    Returns
    -------
    str
        The cache path
    """
    return os.path.join(os.path.expanduser("~"), ".cache", "anemoi", collection)


def clean_cache(collection: str = "default") -> None:
    """Clean the cache for a collection.

    Parameters
    ----------
    collection : str, optional
        The name of the collection, by default "default"
    """
    global CACHE
    CACHE = {}
    path = _get_cache_path(collection)
    if not os.path.exists(path):
        return
    for filename in os.listdir(path):
        os.remove(os.path.join(path, filename))


class Cacher:
    """This class implements a simple caching mechanism.
    Private class, do not use directly.
    """

    def __init__(self, collection: str, expires: Optional[int]):
        """Initialize the Cacher.

        Parameters
        ----------
        collection : str
            The name of the collection
        expires : int, optional
            The expiration time in seconds, or None for no expiration
        """
        self.collection = collection
        self.expires = expires

    def __call__(self, func: Callable) -> Callable:
        """Wrap a function with caching.

        Parameters
        ----------
        func : Callable
            The function to wrap

        Returns
        -------
        Callable
            The wrapped function
        """
        full = f"{func.__module__}.{func.__name__}"

        def wrapped(*args, **kwargs):
            with LOCK:
                return self.cache(
                    (full, args, kwargs),
                    lambda: func(*args, **kwargs),
                )

        return wrapped

    def cache(self, key: tuple, proc: Callable) -> Any:
        """Cache the result of a function.

        Parameters
        ----------
        key : tuple
            The cache key
        proc : Callable
            The function to call if the result is not cached

        Returns
        -------
        Any
            The cached result
        """
        key = json.dumps(key, sort_keys=True)
        m = hashlib.md5()
        m.update(key.encode("utf-8"))
        m = m.hexdigest()

        if m in CACHE:
            return CACHE[m]

        path = _get_cache_path(self.collection)

        filename = os.path.join(path, m) + self.ext
        if os.path.exists(filename):
            data = self.load(filename)
            if self.expires is None or data["expires"] > time.time():
                if data["key"] == key:
                    return data["value"]

        value = proc()
        data = {"key": key, "value": value}
        if self.expires is not None:
            data["expires"] = time.time() + self.expires

        os.makedirs(path, exist_ok=True)
        temp_filename = self.save(filename, data)
        os.rename(temp_filename, filename)

        CACHE[m] = value
        return value


class JsonCacher(Cacher):
    """Cacher that uses JSON files."""

    ext = ""

    def save(self, path: str, data: dict) -> str:
        """Save data to a JSON file.

        Parameters
        ----------
        path : str
            The path to the JSON file
        data : dict
            The data to save

        Returns
        -------
        str
            The temporary file path
        """
        temp_path = path + ".tmp"
        with open(temp_path, "w") as f:
            json.dump(data, f)
        return temp_path

    def load(self, path: str) -> dict:
        """Load data from a JSON file.

        Parameters
        ----------
        path : str
            The path to the JSON file

        Returns
        -------
        dict
            The loaded data
        """
        with open(path, "r") as f:
            return json.load(f)


class NpzCacher(Cacher):
    """Cacher that uses NPZ files."""

    ext = ".npz"

    def save(self, path: str, data: dict) -> str:
        """Save data to an NPZ file.

        Parameters
        ----------
        path : str
            The path to the NPZ file
        data : dict
            The data to save

        Returns
        -------
        str
            The temporary file path
        """
        temp_path = path + ".tmp.npz"
        np.savez(temp_path, **data)
        return temp_path

    def load(self, path: str) -> dict:
        """Load data from an NPZ file.

        Parameters
        ----------
        path : str
            The path to the NPZ file

        Returns
        -------
        dict
            The loaded data
        """
        return np.load(path, allow_pickle=True)


# This function is the main entry point for the caching mechanism for the other anemoi packages
def cached(collection: str = "default", expires: Optional[int] = None, encoding: str = "json") -> Callable:
    """Decorator to cache the result of a function.

    Default is to use a json file to store the cache, but you can also use npz files
    to cache dict of numpy arrays.

    Parameters
    ----------
    collection : str, optional
        The name of the collection, by default "default"
    expires : int, optional
        The expiration time in seconds, or None for no expiration, by default None
    encoding : str, optional
        The encoding type, either "json" or "npz", by default "json"

    Returns
    -------
    Callable
        The decorated function
    """
    return dict(json=JsonCacher, npz=NpzCacher)[encoding](collection, expires)
