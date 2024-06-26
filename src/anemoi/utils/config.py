# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import json
import logging
import os
import threading

import yaml

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

            if isinstance(v, list):
                self[k] = [DotDict(i) if isinstance(i, dict) else i for i in v]

            if isinstance(v, tuple):
                self[k] = [DotDict(i) if isinstance(i, dict) else i for i in v]

    @classmethod
    def from_file(cls, path: str):
        _, ext = os.path.splitext(path)
        if ext == ".yaml" or ext == ".yml":
            return cls.from_yaml_file(path)
        elif ext == ".json":
            return cls.from_json_file(path)
        elif ext == ".toml":
            return cls.from_toml_file(path)
        else:
            raise ValueError(f"Unknown file extension {ext}")

    @classmethod
    def from_yaml_file(cls, path: str):
        with open(path, "r") as file:
            data = yaml.safe_load(file)

        return cls(data)

    @classmethod
    def from_json_file(cls, path: str):
        with open(path, "r") as file:
            data = json.load(file)

        return cls(data)

    @classmethod
    def from_toml_file(cls, path: str):
        with open(path, "r") as file:
            data = tomllib.load(file)
        return cls(data)

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


def config_path(name="settings.toml"):
    full = os.path.join(os.path.expanduser("~"), ".config", "anemoi", name)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    return full


def _load_config():
    global CONFIG
    if CONFIG is not None:
        return CONFIG

    conf = config_path()
    if not os.path.exists(conf):
        if os.path.exists(os.path.expanduser("~/.anemoi.toml")):
            LOG.warning("Configuration file found at ~/.anemoi.toml. Please move it to ~/.config/anemoi/settings.toml")
            conf = os.path.expanduser("~/.anemoi.toml")
    else:
        if os.path.exists(os.path.expanduser("~/.anemoi.toml")):
            LOG.warning(
                "Configuration file found at ~/.anemoi.toml and ~/.config/anemoi/settings.toml, ignoring the former"
            )

    if os.path.exists(conf):
        with open(conf, "rb") as f:
            CONFIG = tomllib.load(f)
    else:
        CONFIG = {}

    return DotDict(CONFIG)


def load_config():
    """Load the configuration`.

    Returns
    -------
    DotDict
        The configuration
    """
    with CONFIG_LOCK:
        return _load_config()


def check_config_mode():
    conf = config_path()
    mode = os.stat(conf).st_mode
    if mode & 0o777 != 0o600:
        raise SystemError(f"Configuration file {conf} is not secure. " "Please run `chmod 600 ~/.anemoi.toml`.")
