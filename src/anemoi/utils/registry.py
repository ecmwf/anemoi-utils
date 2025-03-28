# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import importlib
import logging
import os
import sys
import warnings
from functools import cached_property
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar
from typing import Union

import entrypoints

LOG = logging.getLogger(__name__)

DEBUG_ANEMOI_REGISTRY = int(os.environ.get("DEBUG_ANEMOI_REGISTRY", "0"))


class Wrapper:
    """A wrapper for the registry.

    Parameters
    ----------
    name : str
        The name of the wrapper.
    registry : Registry
        The registry to wrap.
    """

    def __init__(self, name: str, registry: "Registry"):
        self.name = name
        self.registry = registry

    def __call__(self, factory: Callable) -> Callable:
        """Register a factory with the registry.

        Parameters
        ----------
        factory : Callable
            The factory to register.

        Returns
        -------
        Callable
            The registered factory.
        """
        self.registry.register(self.name, factory)
        return factory


class Error:
    """An error class. Used in place of a plugin that failed to load.

    Parameters
    ----------
    error : Exception
        The error.
    """

    def __init__(self, error: Exception):
        self.error = error

    def __call__(self, *args, **kwargs):
        raise self.error


_BY_KIND = {}

T = TypeVar("T")


class Registry(Generic[T]):
    """A registry of factories.

    Parameters
    ----------
    package : str
        The package name.
    key : str, optional
        The key to use for the registry, by default "_type".
    api_version : str, optional
        The API version, by default '1.0.0'.
    """

    def __init__(self, package: str, key: str = "_type", api_version: str = "1.0.0"):
        self.package = package
        self.__registered = {}
        self._sources = {}
        self.kind = package.split(".")[-1]
        self.key = key
        self.api_version = api_version
        _BY_KIND[self.kind] = self

    @classmethod
    def lookup_kind(cls, kind: str) -> Optional["Registry"]:
        """Lookup a registry by kind.

        Parameters
        ----------
        kind : str
            The kind of the registry.

        Returns
        -------
        Registry, optional
            The registry if found, otherwise None.
        """
        return _BY_KIND.get(kind)

    def register(
        self, name: str, factory: Optional[Callable] = None, source: Optional[Any] = None
    ) -> Optional[Wrapper]:
        """Register a factory with the registry.

        Parameters
        ----------
        name : str
            The name of the factory.
        factory : Callable, optional
            The factory to register, by default None.
        source : Any, optional
            The source of the factory, by default None.

        Returns
        -------
        Wrapper, optional
            A wrapper if the factory is None, otherwise None.
        """

        name = name.replace("_", "-")

        if factory is None:
            # This happens when the @register decorator is used
            return Wrapper(name, self)

        if source is None:
            source = getattr(factory, "_source") if hasattr(factory, "_source") else factory

        if name in self.__registered:
            warnings.warn(f"Factory '{name}' is already registered in {self.package}")
            warnings.warn(f"Existing: {self._sources[name]}")
            warnings.warn(f"New: {source}")

        self.__registered[name] = factory
        self._sources[name] = source

    def _load(self, file: str) -> None:
        """Load a module from a file.

        Parameters
        ----------
        file : str
            The file to load.
        """

        name, _ = os.path.splitext(file)

        try:
            importlib.import_module(f".{name}", package=self.package)
        except Exception as e:
            if DEBUG_ANEMOI_REGISTRY:
                raise

            name = name.replace("_", "-")
            self.__registered[name] = Error(e)

    def is_registered(self, name: str) -> bool:
        """Check if a factory is registered.

        Parameters
        ----------
        name : str
            The name of the factory.

        Returns
        -------
        bool
            Whether the factory is registered.
        """

        name = name.replace("_", "-")

        ok = name in self.factories
        if not ok:
            LOG.error(f"Cannot find '{name}' in {self.package}")
            for e in self.factories:
                LOG.info(f"Registered: {e} ({self._sources.get(e)})")
        return ok

    def lookup(self, name: str, *, return_none: bool = False) -> Optional[Callable]:
        """Lookup a factory by name.

        Parameters
        ----------
        name : str
            The name of the factory.
        return_none : bool, optional
            Whether to return None if the factory is not found, by default False.

        Returns
        -------
        Callable, optional
            The factory if found, otherwise None.
        """

        name = name.replace("_", "-")

        if return_none:
            return self.factories.get(name)

        factory = self.factories.get(name)
        if factory is None:

            LOG.error(f"Cannot find '{name}' in {self.package}")
            for e in self.factories:
                LOG.info(f"Registered: {e} ({self._sources.get(e)})")

            raise ValueError(f"Cannot find '{name}' in {self.package}")

        return factory

    @cached_property
    def factories(self) -> Dict[str, Callable]:

        directory = sys.modules[self.package].__path__[0]

        for file in os.listdir(directory):

            if file[0] == ".":
                continue

            if file == "__init__.py":
                continue

            full = os.path.join(directory, file)
            if os.path.isdir(full):
                if os.path.exists(os.path.join(full, "__init__.py")):
                    self._load(file)
                continue

            if file.endswith(".py"):
                self._load(file)

        bits = self.package.split(".")
        # We assume a name like anemoi.datasets.create.sources, with kind = sources
        assert bits[-1] == self.kind, (self.package, self.kind)
        assert len(bits) > 1, self.package

        groups = []
        middle = bits[1:-1]
        while True:
            group = ".".join([bits[0], *middle, bits[-1]])
            groups.append(group)
            if len(middle) == 0:
                break
            middle.pop()

        groups.reverse()

        LOG.debug("Loading plugins from %s", groups)

        for entrypoint_group in groups:
            for entry_point in entrypoints.get_group_all(entrypoint_group):
                source = entry_point.distro
                try:
                    self.register(entry_point.name, entry_point.load(), source=source)
                except Exception as e:
                    if DEBUG_ANEMOI_REGISTRY:
                        raise
                    self.register(entry_point.name, Error(e), source=source)

        return self.__registered

    @property
    def registered(self) -> List[str]:
        """Get the registered factories."""

        return sorted(self.factories.keys())

    def create(self, name: str, *args: Any, **kwargs: Any) -> T:
        """Create an instance using a factory.

        Parameters
        ----------
        name : str
            The name of the factory.
        *args : Any
            Positional arguments for the factory.
        **kwargs : Any
            Keyword arguments for the factory.

        Returns
        -------
        Any
            The created instance.
        """

        name = name.replace("_", "-")

        factory = self.lookup(name)
        return factory(*args, **kwargs)

    def from_config(self, config: Union[str, Dict[str, Any]], *args: Any, **kwargs: Any) -> T:
        """Create an instance from a configuration.

        Parameters
        ----------
        config : str or dict
            The configuration.
        *args : Any
            Positional arguments for the factory.
        **kwargs : Any
            Keyword arguments for the factory.

        Returns
        -------
        Any
            The created instance.
        """
        if isinstance(config, str):
            config = {config: {}}

        if not isinstance(config, dict):
            raise ValueError(f"Invalid config: {config}")

        if self.key in config:
            config = config.copy()
            key = config.pop(self.key)
            return self.create(key, *args, **config, **kwargs)

        if len(config) == 1:
            key = list(config.keys())[0]
            value = config[key]

            if isinstance(value, dict):
                return self.create(key, *args, **value, **kwargs)

            if isinstance(value, list):
                return self.create(key, *args, *value, **kwargs)

            return self.create(key, *args, value, **kwargs)

        raise ValueError(
            f"Entry '{config}' must either be a string, a dictionary with a single entry, or a dictionary with a '{self.key}' key"
        )
