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

import numpy as np

LOCK = Lock()
CACHE = {}


def _get_cache_path(collection):
    return os.path.join(os.path.expanduser("~"), ".cache", "anemoi", collection)


def clean_cache(collection="default"):
    global CACHE
    CACHE = {}
    path = _get_cache_path(collection)
    if not os.path.exists(path):
        return
    for filename in os.listdir(path):
        os.remove(os.path.join(path, filename))


class Cacher:
    """This class implements a simple caching mechanism.
    Private class, do not use directly"""

    def __init__(self, collection, expires):
        self.collection = collection
        self.expires = expires

    def __call__(self, func):

        full = f"{func.__module__}.{func.__name__}"

        def wrapped(*args, **kwargs):
            with LOCK:
                return self.cache(
                    (full, args, kwargs),
                    lambda: func(*args, **kwargs),
                )

        return wrapped

    def cache(self, key, proc):

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
    ext = ""

    def save(self, path, data):
        temp_path = path + ".tmp"
        with open(temp_path, "w") as f:
            json.dump(data, f)
        return temp_path

    def load(self, path):
        with open(path, "r") as f:
            return json.load(f)


class NpzCacher(Cacher):
    ext = ".npz"

    def save(self, path, data):
        temp_path = path + ".tmp.npz"
        np.savez(temp_path, **data)
        return temp_path

    def load(self, path):
        return np.load(path, allow_pickle=True)


# PUBLIC API
def cached(collection="default", expires=None, encoding="json"):
    """Decorator to cache the result of a function.

    Default is to use a json file to store the cache, but you can also use npz files
    to cache dict of numpy arrays.

    """
    return dict(json=JsonCacher, npz=NpzCacher)[encoding](collection, expires)
