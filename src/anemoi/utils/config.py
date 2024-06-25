# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging
import os
import threading

try:
    import tomllib  # Only available since 3.11
except ImportError:
    import tomli as tomllib


LOG = logging.getLogger(__name__)


class DotDict(dict):
    """A dictionary that allows access to its keys as attributes.

    >>> d = DotDict({"a": 1, "b": {"c": 2}})
    >>> d.a
    1
    >>> d.b.c
    2
    >>> d.b = 3
    >>> d.b
    3

    The class is recursive, so nested dictionaries are also DotDicts.

    The DotDict class has the same constructor as the dict class.

    >>> d = DotDict(a=1, b=2)

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for k, v in self.items():
            if isinstance(v, dict):
                self[k] = DotDict(v)

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        if isinstance(value, dict):
            value = DotDict(value)
        self[attr] = value

    def __repr__(self) -> str:
        return f"DotDict({super().__repr__()})"


CONFIG = None
CONFIG_LOCK = threading.Lock()


def _load_config():
    global CONFIG
    if CONFIG is not None:
        return CONFIG

    conf = os.path.expanduser("~/.anemoi.toml")

    if os.path.exists(conf):

        with open(conf, "rb") as f:
            CONFIG = tomllib.load(f)
    else:
        CONFIG = {}

    return DotDict(CONFIG)


def load_config():
    """Load the configuration from `~/.anemoi.toml`.

    Returns
    -------
    DotDict
        The configuration
    """
    with CONFIG_LOCK:
        return _load_config()


def check_config_mode():
    conf = os.path.expanduser("~/.anemoi.toml")
    mode = os.stat(conf).st_mode
    if mode & 0o777 != 0o600:
        raise SystemError(f"Configuration file {conf} is not secure. " "Please run `chmod 600 ~/.anemoi.toml`.")
