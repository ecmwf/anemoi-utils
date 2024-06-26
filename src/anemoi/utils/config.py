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


CONFIG = {}
CHECKED = {}
CONFIG_LOCK = threading.Lock()
QUIET = False


def config_path(name="settings.toml"):
    global QUIET
    full = os.path.join(os.path.expanduser("~"), ".config", "anemoi", name)
    os.makedirs(os.path.dirname(full), exist_ok=True)

    if name == "settings.toml":
        old = os.path.join(os.path.expanduser("~"), ".anemoi.toml")
        if not os.path.exists(full) and os.path.exists(old):
            if not QUIET:
                LOG.warning(
                    "Configuration file found at ~/.anemoi.toml. Please move it to ~/.config/anemoi/settings.toml"
                )
                QUIET = True
            return old
        else:
            if os.path.exists(old):
                if not QUIET:
                    LOG.warning(
                        "Configuration file found at ~/.anemoi.toml and ~/.config/anemoi/settings.toml, ignoring the former"
                    )
                    QUIET = True

    return full


def _load(path):
    try:
        if path.endswith(".json"):
            with open(path, "rb") as f:
                return json.load(f)

        if path.endswith(".yaml") or path.endswith(".yml"):
            with open(path, "rb") as f:
                return yaml.safe_load(f)

        if path.endswith(".toml"):
            with open(path, "rb") as f:
                return tomllib.load(f)
    except (json.JSONDecodeError, yaml.YAMLError, tomllib.TOMLDecodeError) as e:
        LOG.warning(f"Failed to parse config file {path}", exc_info=e)
        return {}

    return open(path).read()


def _load_config(name="settings.toml"):

    if name in CONFIG:
        return CONFIG[name]

    conf = config_path(name)

    if os.path.exists(conf):
        config = _load(conf)
    else:
        config = {}

    if isinstance(config, dict):
        CONFIG[name] = DotDict(config)
    else:
        CONFIG[name] = config

    return CONFIG[name]


def _save_config(name, data):
    CONFIG.pop(name, None)

    conf = config_path(name)

    if conf.endswith(".json"):
        with open(conf, "w") as f:
            json.dump(data, f, indent=4)
        return

    if conf.endswith(".yaml") or conf.endswith(".yml"):
        with open(conf, "w") as f:
            yaml.dump(data, f)
        return

    if conf.endswith(".toml"):
        raise NotImplementedError("Saving to TOML is not implemented yet")

    with open(conf, "w") as f:
        f.write(data)


def save_config(name, data):
    """Save a configuration file.

    Parameters
    ----------
    name : str
        The name of the configuration file to save.

    data : Any
        The data to save.

    """
    with CONFIG_LOCK:
        _save_config(name, data)


def load_config(name="settings.toml"):
    """Read a configuration file.

    Parameters
    ----------
    name : str, optional
        The name of the config file to read, by default "settings.toml"

    Returns
    -------
    DotDict or str
        Return DotDict if it is a dictionary, otherwise the raw data
    """
    with CONFIG_LOCK:
        return _load_config(name)


def check_config_mode(name="settings.toml"):
    """Check that a configuration file is secure.

    Parameters
    ----------
    name : str, optional
        The name of the configuration file, by default "settings.toml"

    Raises
    ------
    SystemError
        If the configuration file is not secure.
    """
    with CONFIG_LOCK:
        if name in CHECKED:
            return
        conf = config_path(name)
        mode = os.stat(conf).st_mode
        if mode & 0o777 != 0o600:
            raise SystemError(f"Configuration file {conf} is not secure. " "Please run `chmod 600 {conf}`.")
        CHECKED[name] = True
