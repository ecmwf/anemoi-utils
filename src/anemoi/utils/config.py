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
from typing import Any
from typing import Optional
from typing import Union

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
        """Initialize a DotDict instance.

        Parameters
        ----------
        *args : tuple
            Positional arguments for the dict constructor.
        **kwargs : dict
            Keyword arguments for the dict constructor.
        """
        super().__init__(*args, **kwargs)

        for k, v in self.items():
            if isinstance(v, dict) or is_omegaconf_dict(v):
                self[k] = DotDict(v)

            if isinstance(v, list) or is_omegaconf_list(v):
                self[k] = [DotDict(i) if isinstance(i, dict) or is_omegaconf_dict(i) else i for i in v]

            if isinstance(v, tuple):
                self[k] = [DotDict(i) if isinstance(i, dict) or is_omegaconf_dict(i) else i for i in v]

    @classmethod
    def from_file(cls, path: str) -> DotDict:
        """Create a DotDict from a file.

        Parameters
        ----------
        path : str
            The path to the file.

        Returns
        -------
        DotDict
            The created DotDict.
        """
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
    def from_yaml_file(cls, path: str) -> DotDict:
        """Create a DotDict from a YAML file.

        Parameters
        ----------
        path : str
            The path to the YAML file.

        Returns
        -------
        DotDict
            The created DotDict.
        """
        with open(path, "r") as file:
            data = yaml.safe_load(file)

        return cls(data)

    @classmethod
    def from_json_file(cls, path: str) -> DotDict:
        """Create a DotDict from a JSON file.

        Parameters
        ----------
        path : str
            The path to the JSON file.

        Returns
        -------
        DotDict
            The created DotDict.
        """
        with open(path, "r") as file:
            data = json.load(file)

        return cls(data)

    @classmethod
    def from_toml_file(cls, path: str) -> DotDict:
        """Create a DotDict from a TOML file.

        Parameters
        ----------
        path : str
            The path to the TOML file.

        Returns
        -------
        DotDict
            The created DotDict.
        """
        with open(path, "r") as file:
            data = tomllib.load(file)
        return cls(data)

    def __getattr__(self, attr: str) -> Any:
        """Get an attribute.

        Parameters
        ----------
        attr : str
            The attribute name.

        Returns
        -------
        Any
            The attribute value.
        """
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

    def __setattr__(self, attr: str, value: Any) -> None:
        """Set an attribute.

        Parameters
        ----------
        attr : str
            The attribute name.
        value : Any
            The attribute value.
        """
        if isinstance(value, dict):
            value = DotDict(value)
        self[attr] = value

    def __repr__(self) -> str:
        """Return a string representation of the DotDict.

        Returns
        -------
        str
            The string representation.
        """
        return f"DotDict({super().__repr__()})"


def is_omegaconf_dict(value: Any) -> bool:
    """Check if a value is an OmegaConf DictConfig.

    Parameters
    ----------
    value : Any
        The value to check.

    Returns
    -------
    bool
        True if the value is a DictConfig, False otherwise.
    """
    try:
        from omegaconf import DictConfig

        return isinstance(value, DictConfig)
    except ImportError:
        return False


def is_omegaconf_list(value: Any) -> bool:
    """Check if a value is an OmegaConf ListConfig.

    Parameters
    ----------
    value : Any
        The value to check.

    Returns
    -------
    bool
        True if the value is a ListConfig, False otherwise.
    """
    try:
        from omegaconf import ListConfig

        return isinstance(value, ListConfig)
    except ImportError:
        return False


CONFIG = {}
CHECKED = {}
CONFIG_LOCK = threading.RLock()
QUIET = False


def _find(config: Union[dict, list], what: str, result: list = None) -> list:
    """Find all occurrences of a key in a nested dictionary or list.

    Parameters
    ----------
    config : dict or list
        The configuration to search.
    what : str
        The key to search for.
    result : list, optional
        The list to store results, by default None.

    Returns
    -------
    list
        The list of found values.
    """
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


def _merge_dicts(a: dict, b: dict) -> None:
    """Merge two dictionaries recursively.

    Parameters
    ----------
    a : dict
        The first dictionary.
    b : dict
        The second dictionary.
    """
    for k, v in b.items():
        if k in a and isinstance(a[k], dict) and isinstance(v, dict):
            _merge_dicts(a[k], v)
        else:
            a[k] = v


def _set_defaults(a: dict, b: dict) -> None:
    """Set default values in a dictionary.

    Parameters
    ----------
    a : dict
        The dictionary to set defaults in.
    b : dict
        The dictionary with default values.
    """
    for k, v in b.items():
        if k in a and isinstance(a[k], dict) and isinstance(v, dict):
            _set_defaults(a[k], v)
        else:
            a.setdefault(k, v)


def config_path(name: str = "settings.toml") -> str:
    """Get the path to a configuration file.

    Parameters
    ----------
    name : str, optional
        The name of the configuration file, by default "settings.toml".

    Returns
    -------
    str
        The path to the configuration file.
    """
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


def load_any_dict_format(path: str) -> dict:
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

        if path == "-":
            import sys

            config = sys.stdin.read()

            parsers = [(yaml.safe_load, "yaml"), (json.loads, "json"), (tomllib.loads, "toml")]

            for parser, parser_type in parsers:
                try:
                    LOG.debug(f"Trying {parser_type} parser for stdin")
                    return parser(config)
                except Exception:
                    pass

            raise ValueError("Failed to parse configuration from stdin")

    except (json.JSONDecodeError, yaml.YAMLError, tomllib.TOMLDecodeError) as e:
        LOG.warning(f"Failed to parse config file {path}", exc_info=e)
        raise ValueError(f"Failed to parse config file {path} [{e}]")

    return open(path).read()


def _load_config(
    name: str = "settings.toml",
    secrets: Optional[Union[str, list[str]]] = None,
    defaults: Optional[Union[str, dict]] = None,
) -> DotDict:
    """Load a configuration file.

    Parameters
    ----------
    name : str, optional
        The name of the configuration file, by default "settings.toml".
    secrets : str or list, optional
        The name of the secrets file, by default None.
    defaults : str or dict, optional
        The name of the defaults file, by default None.

    Returns
    -------
    DotDict
        The loaded configuration.
    """
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

    for env, value in os.environ.items():

        if not env.startswith("ANEMOI_CONFIG_"):
            continue
        rest = env[len("ANEMOI_CONFIG_") :]

        package = rest.split("_")[0]
        sub = rest[len(package) + 1 :]

        package = package.lower()
        sub = sub.lower()

        LOG.info(f"Using environment variable {env} to override the anemoi config key '{package}.{sub}'")

        if package not in config:
            config[package] = {}
        config[package][sub] = value

    CONFIG[key] = DotDict(config)
    return CONFIG[key]


def _save_config(name: str, data: Any) -> None:
    """Save a configuration file.

    Parameters
    ----------
    name : str
        The name of the configuration file.
    data : Any
        The data to save.
    """
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


def save_config(name: str, data: Any) -> None:
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


def load_config(
    name: str = "settings.toml",
    secrets: Optional[Union[str, list[str]]] = None,
    defaults: Optional[Union[str, dict]] = None,
) -> DotDict | str:
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


def load_raw_config(name: str, default: Any = None) -> Union[DotDict, str]:
    """Load a raw configuration file.

    Parameters
    ----------
    name : str
        The name of the configuration file.
    default : Any, optional
        The default value if the file does not exist, by default None.

    Returns
    -------
    DotDict or str
        The loaded configuration or the default value.
    """
    path = config_path(name)
    if os.path.exists(path):
        return load_any_dict_format(path)

    return default


def check_config_mode(name: str = "settings.toml", secrets_name: str = None, secrets: list[str] = None) -> None:
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


def find(metadata: Union[dict, list], what: str, result: list = None, *, select: callable = None) -> list:
    """Find all occurrences of a key in a nested dictionary or list with an optional selector.

    Parameters
    ----------
    metadata : dict or list
        The metadata to search.
    what : str
        The key to search for.
    result : list, optional
        The list to store results, by default None.
    select : callable, optional
        A function to filter the results, by default None.

    Returns
    -------
    list
        The list of found values.
    """
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


def merge_configs(*configs: dict) -> dict:
    """Merge multiple configuration dictionaries.

    Parameters
    ----------
    *configs : dict
        The configuration dictionaries to merge.

    Returns
    -------
    dict
        The merged configuration dictionary.
    """
    result = {}
    for config in configs:
        _merge_dicts(result, config)

    return result
