# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import hashlib
import json
import os
import time


def cache(key, proc, collection="default", expires=None):
    path = os.path.join(os.path.expanduser("~"), ".cache", "anemoi", collection)
    os.makedirs(path, exist_ok=True)

    key = json.dumps(key, sort_keys=True)
    m = hashlib.md5()
    m.update(key.encode("utf-8"))

    filename = os.path.join(path, m.hexdigest())
    if os.path.exists(filename):
        with open(filename, "r") as f:
            data = json.load(f)
            if expires is None or data["expires"] > time.time():
                if data["key"] == key:
                    return data["value"]

    value = proc()
    data = {"key": key, "value": value}
    if expires is not None:
        data["expires"] = time.time() + expires

    with open(filename, "w") as f:
        json.dump(data, f)

    return value


class cached:

    def __init__(self, collection="default", expires=None):
        self.collection = collection
        self.expires = expires

    def __call__(self, func):

        full = f"{func.__module__}.{func.__name__}"

        def wrapped(*args, **kwargs):
            return cache(
                (full, args, kwargs),
                lambda: func(*args, **kwargs),
                self.collection,
                self.expires,
            )

        return wrapped
