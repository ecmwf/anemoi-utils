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


def _json_save(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def _json_load(path):
    with open(path, "r") as f:
        return json.load(f)


def _npz_save(path, data):
    return np.savez(path, **data)


def _npz_load(path):
    return np.load(path, allow_pickle=True)


def _get_cache_path(collection):
    return os.path.join(os.path.expanduser("~"), ".cache", "anemoi", collection)


def clean_cache(collection="default"):
    path = _get_cache_path(collection)
    if not os.path.exists(path):
        return
    for filename in os.listdir(path):
        os.remove(os.path.join(path, filename))


def cache(key, proc, collection="default", expires=None, encoding="json"):
    load, save, ext = dict(
        json=(_json_load, _json_save, ""),
        npz=(_npz_load, _npz_save, ".npz"),
    )[encoding]

    key = json.dumps(key, sort_keys=True)
    m = hashlib.md5()
    m.update(key.encode("utf-8"))
    m = m.hexdigest()

    if m in CACHE:
        return CACHE[m]

    path = _get_cache_path(collection)

    filename = os.path.join(path, m) + ext
    if os.path.exists(filename):
        data = load(filename)
        if expires is None or data["expires"] > time.time():
            if data["key"] == key:
                return data["value"]

    value = proc()
    data = {"key": key, "value": value}
    if expires is not None:
        data["expires"] = time.time() + expires

    os.makedirs(path, exist_ok=True)
    save(filename, data)

    CACHE[m] = value
    return value


class cached:
    """Decorator to cache the result of a function."""

    def __init__(self, collection="default", expires=None, encoding="json"):
        self.collection = collection
        self.expires = expires
        self.encoding = encoding

    def __call__(self, func):

        full = f"{func.__module__}.{func.__name__}"

        def wrapped(*args, **kwargs):
            with LOCK:
                return cache(
                    (full, args, kwargs),
                    lambda: func(*args, **kwargs),
                    self.collection,
                    self.expires,
                    self.encoding,
                )

        return wrapped
