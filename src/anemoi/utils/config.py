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
from typing import Any

import deprecation
import omegaconf.dictconfig
import yaml

from anemoi.utils._version import __version__

try:
    import tomllib  # Only available since 3.11
except ImportError:
    import tomli as tomllib


LOG = logging.getLogger(__name__)


class DotDict(omegaconf.dictconfig.DictConfig):
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

    def __init__(
        self,
        *args: Any,
        resolve_interpolations: bool = False,
        cli_arguments: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialise a DotDict instance.

        Parameters
        ----------
        *args : Any
            Arguments to construct the dictionary.
        resolve_interpolations : bool, optional
            Whether to resolve interpolations, by default False.
        cli_arguments : list of str, optional
            CLI arguments to override values, by default None.
        **kwargs : Any
            Keyword arguments to construct the dictionary.
        """

        # Allow non-primitive types like datetime by enabling allow_objects

        d = omegaconf.OmegaConf.create(dict(*args, **kwargs), flags={"allow_objects": True})

        if cli_arguments:
            d = omegaconf.OmegaConf.merge(d, omegaconf.OmegaConf.from_cli(cli_arguments))

        if resolve_interpolations:
            d = omegaconf.OmegaConf.to_container(d, resolve=True)

        return super().__init__(d)

    @classmethod
    def from_file(
        cls: type["DotDict"],
        path: str,
        *args: Any,
        resolve_interpolations: bool = False,
        cli_arguments: list[str] | None = None,
        **kwargs: Any,
    ) -> "DotDict":
        """Create a DotDict from a file."""
        _, ext = os.path.splitext(path)

        match ext:
            case ".yaml" | ".yml":
                return cls.from_yaml_file(
                    path,
                    *args,
                    resolve_interpolations=resolve_interpolations,
                    cli_arguments=cli_arguments,
                    **kwargs,
                )
            case ".json":
                return cls.from_json_file(
                    path,
                    *args,
                    resolve_interpolations=resolve_interpolations,
                    cli_arguments=cli_arguments,
                    **kwargs,
                )
            case ".toml":
                return cls.from_toml_file(
                    path,
                    *args,
                    resolve_interpolations=resolve_interpolations,
                    cli_arguments=cli_arguments,
                    **kwargs,
                )
            case _:
                raise ValueError(f"Unknown file extension {ext}")

    @classmethod
    def from_yaml_file(
        cls: type["DotDict"],
        path: str,
        *args: Any,
        resolve_interpolations: bool = False,
        cli_arguments: list[str] | None = None,
        **kwargs: Any,
    ) -> "DotDict":
        """Create a DotDict from a YAML file."""
        with open(path) as file:
            data = yaml.safe_load(file)

        return cls(
            data,
            *args,
            resolve_interpolations=resolve_interpolations,
            cli_arguments=cli_arguments,
            **kwargs,
        )

    @classmethod
    def from_json_file(
        cls: type["DotDict"],
        path: str,
        *args: Any,
        resolve_interpolations: bool = False,
        cli_arguments: list[str] | None = None,
        **kwargs: Any,
    ) -> "DotDict":
        """Create a DotDict from a JSON file."""
        with open(path) as file:
            data = json.load(file)

        return cls(
            data,
            *args,
            resolve_interpolations=resolve_interpolations,
            cli_arguments=cli_arguments,
            **kwargs,
        )

    @classmethod
    def from_toml_file(
        cls: type["DotDict"],
        path: str,
        *args: Any,
        resolve_interpolations: bool = False,
        cli_arguments: list[str] | None = None,
        **kwargs: Any,
    ) -> "DotDict":
        """Create a DotDict from a TOML file."""
        with open(path) as file:
            data = tomllib.load(file)

        return cls(
            data,
            *args,
            resolve_interpolations=resolve_interpolations,
            cli_arguments=cli_arguments,
            **kwargs,
        )

    def __repr__(self) -> str:
        return f"DotDict({super().__repr__()})"

    def to_dict(self, *, resolve_interpolations: bool = True) -> dict:
        """Convert the DotDict to a standard dictionary.

        Parameters
        ----------
        resolve_interpolations : bool, optional
            Whether to resolve any interpolations, by default True.

        Returns
        -------
        dict
            The converted dictionary.
        """
        """Convert the DotDict to a standard dictionary.

        Parameters
        ----------
        resolve : bool, optional
            Whether to resolve any interpolations, by default False.

        Returns
        -------
        dict
            The converted dictionary.
        """
        return omegaconf.OmegaConf.to_container(self, resolve=resolve_interpolations)


def load_any_dict_format(path: str) -> dict:
    """Load a configuration file in any supported format: JSON, YAML, or TOML.

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


def find(metadata: dict | list, what: str, result: list = None, *, select: callable = None) -> list:
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


@deprecation.deprecated(
    deprecated_in="0.4.30",
    removed_in="0.5.0",
    current_version=__version__,
    details="Use anemoi.utils.settings.temporary_settings instead.",
)
def temporary_config(*args, **kwargs) -> None:
    """Deprecated. Use anemoi.utils.settings.temporary_settings instead.

    Parameters
    ----------
    *args : Any
        Arguments to pass to temporary_settings.
    **kwargs : Any
        Keyword arguments to pass to temporary_settings.
    """
    from .settings import temporary_settings

    return temporary_settings(*args, **kwargs)


@deprecation.deprecated(
    deprecated_in="0.4.30",
    removed_in="0.5.0",
    current_version=__version__,
    details="Use anemoi.utils.settings.load_settings instead.",
)
def load_config(*args, **kwargs) -> DotDict | str:
    """Deprecated. Use anemoi.utils.settings.load_settings instead.

    Parameters
    ----------
    *args : Any
        Arguments to pass to load_settings.
    **kwargs : Any
        Keyword arguments to pass to load_settings.

    Returns
    -------
    DotDict or str
        The loaded configuration.
    """
    from .settings import load_settings

    return load_settings(*args, **kwargs)


@deprecation.deprecated(
    deprecated_in="0.4.30",
    removed_in="0.5.0",
    current_version=__version__,
    details="Use anemoi.utils.settings.settings_path instead.",
)
def config_path(*args, **kwargs) -> str:
    """Deprecated. Use anemoi.utils.settings.settings_path instead.

    Parameters
    ----------
    *args : Any
        Arguments to pass to settings_path.
    **kwargs : Any
        Keyword arguments to pass to settings_path.

    Returns
    -------
    str
        The settings path.
    """
    from .settings import settings_path

    return settings_path(*args, **kwargs)


@deprecation.deprecated(
    deprecated_in="0.4.30",
    removed_in="0.5.0",
    current_version=__version__,
    details="Use anemoi.utils.settings.save_settings instead.",
)
def save_config(*args, **kwargs) -> None:
    """Deprecated. Use anemoi.utils.settings.save_settings instead.

    Parameters
    ----------
    *args : Any
        Arguments to pass to save_settings.
    **kwargs : Any
        Keyword arguments to pass to save_settings.
    """
    from .settings import save_settings

    save_settings(*args, **kwargs)


@deprecation.deprecated(
    deprecated_in="0.4.30",
    removed_in="0.5.0",
    current_version=__version__,
    details="Use anemoi.utils.settings.load_settings instead.",
)
def check_config_mode(*args, **kwargs) -> None:
    """Deprecated. Use anemoi.utils.settings.check_settings_mode instead.

    Parameters
    ----------
    *args : Any
        Arguments to pass to check_settings_mode.
    **kwargs : Any
        Keyword arguments to pass to check_settings_mode.
    """
    from .settings import check_settings_mode

    check_settings_mode(*args, **kwargs)


if __name__ == "__main__":
    a = DotDict({"a": 1, "b": {"c": 2}, "user": "${oc.env:HOME}"})
    print(a)
    print(a.a)
    print(a.user)
