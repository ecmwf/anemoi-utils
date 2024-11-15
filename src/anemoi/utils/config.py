# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from __future__ import annotations

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
CONFIG_LOCK = threading.RLock()
QUIET = False


def _find(config, what, result=None):
    if result is None:
        result = []

    if isinstance(config, list):
        for i in config:
            _find(i, what, result)
        return result

    if isinstance(config, dict):
        if what in config:
            result.append(config[what])

        for k, v in config.items():
            _find(v, what, result)

    return result


def _merge_dicts(a, b):
    for k, v in b.items():
        if k in a and isinstance(a[k], dict) and isinstance(v, dict):
            _merge_dicts(a[k], v)
        else:
            a[k] = v


def _set_defaults(a, b):
    for k, v in b.items():
        if k in a and isinstance(a[k], dict) and isinstance(v, dict):
            _set_defaults(a[k], v)
        else:
            a.setdefault(k, v)


def config_path(name="settings.toml"):
    global QUIET

    if name.startswith("/") or name.startswith("."):
        return name

    if name.startswith("~"):
        return os.path.expanduser(name)

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


def load_any_dict_format(path) -> dict:
    """Load a configuration file in any supported format: JSON, YAML and TOML.

    Parameters
    ----------
    path : str
        The path to the configuration file.

    Returns
    -------
    dict
        The decoded configuration file.
    """

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
        raise ValueError(f"Failed to parse config file {path} [{e}]")

    return open(path).read()


def _load_config(name="settings.toml", secrets=None, defaults=None):

    key = json.dumps((name, secrets, defaults), sort_keys=True, default=str)
    if key in CONFIG:
        return CONFIG[key]

    path = config_path(name)
    if os.path.exists(path):
        config = load_any_dict_format(path)
    else:
        config = {}

    if defaults is not None:
        if isinstance(defaults, str):
            defaults = load_raw_config(defaults)
        _set_defaults(config, defaults)

    if secrets is not None:
        if isinstance(secrets, str):
            secrets = [secrets]

        base, ext = os.path.splitext(path)
        secret_name = base + ".secrets" + ext

        found = set()
        for secret in secrets:
            if _find(config, secret):
                found.add(secret)

        if found:
            check_config_mode(name, secret_name, found)

        check_config_mode(secret_name, None)
        secret_config = _load_config(secret_name)
        _merge_dicts(config, secret_config)

    CONFIG[key] = DotDict(config)
    return CONFIG[key]


def _save_config(name, data) -> None:
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


def save_config(name, data) -> None:
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


def load_config(name="settings.toml", secrets=None, defaults=None) -> DotDict | str:
    """Read a configuration file.

    Parameters
    ----------
    name : str, optional
        The name of the config file to read, by default "settings.toml"
    secrets : str or list, optional
        The name of the secrets file, by default None
    defaults : str or dict, optional
        The name of the defaults file, by default None

    Returns
    -------
    DotDict or str
        Return DotDict if it is a dictionary, otherwise the raw data
    """

    with CONFIG_LOCK:
        return _load_config(name, secrets, defaults)


def load_raw_config(name, default=None) -> DotDict | str:

    path = config_path(name)
    if os.path.exists(path):
        return load_any_dict_format(path)

    return default


def check_config_mode(name="settings.toml", secrets_name=None, secrets=None) -> None:
    """Check that a configuration file is secure.

    Parameters
    ----------
    name : str, optional
        The name of the configuration file, by default "settings.toml"
    secrets_name : str, optional
        The name of the secrets file, by default None
    secrets : list, optional
        The list of secrets to check, by default None

    Raises
    ------
    SystemError
        If the configuration file is not secure.
    """
    with CONFIG_LOCK:
        if name in CHECKED:
            return

        conf = config_path(name)
        if not os.path.exists(conf):
            return
        mode = os.stat(conf).st_mode
        if mode & 0o777 != 0o600:
            if secrets_name:
                secret_path = config_path(secrets_name)
                raise SystemError(
                    f"Configuration file {conf} should not hold entries {secrets}.\n"
                    f"Please move them to {secret_path}."
                )
            raise SystemError(f"Configuration file {conf} is not secure.\n" f"Please run `chmod 600 {conf}`.")

        CHECKED[name] = True


def find(metadata, what, result=None, *, select: callable = None):
    if result is None:
        result = []

    if isinstance(metadata, list):
        for i in metadata:
            find(i, what, result)
        return result

    if isinstance(metadata, dict):
        if what in metadata:
            if select is None or select(metadata[what]):
                result.append(metadata[what])

        for k, v in metadata.items():
            find(v, what, result)

    return result
