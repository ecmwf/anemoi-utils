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
from functools import cached_property

import entrypoints

LOG = logging.getLogger(__name__)


class Wrapper:
    """A wrapper for the registry"""

    def __init__(self, name, registry):
        self.name = name
        self.registry = registry

    def __call__(self, factory):
        self.registry.register(self.name, factory)
        return factory


_BY_KIND = {}


class Registry:
    """A registry of factories"""

    def __init__(self, package, key="_type"):

        self.package = package
        self._registered = {}
        self.kind = package.split(".")[-1]
        self.key = key
        _BY_KIND[self.kind] = self

    @classmethod
    def lookup_kind(cls, kind: str):
        return _BY_KIND.get(kind)

    def register(self, name: str, factory: callable = None):

        if factory is None:
            return Wrapper(name, self)

        self._registered[name] = factory

    def names(self):

        package = importlib.import_module(self.package)
        root = os.path.dirname(package.__file__)
        result = []

        for file in os.listdir(root):
            if file[0] == ".":
                continue
            if file == "__init__.py":
                continue
            if file.endswith(".py"):
                result.append(file[:-3])
            if os.path.isdir(os.path.join(root, file)):
                if os.path.exists(os.path.join(root, file, "__init__.py")):
                    result.append(file)
        return result

    def _load(self, file):
        name, _ = os.path.splitext(file)
        try:
            importlib.import_module(f".{name}", package=self.package)
        except Exception:
            LOG.warning(f"Error loading filter '{self.package}.{name}'", exc_info=True)

    def lookup(self, name: str, *, return_none=False) -> callable:

        if name not in self.registered:
            if return_none:
                return None

            for e in self._registered:
                LOG.info(f"Registered: {e}")

            raise ValueError(f"Cannot load '{name}' from {self.package}")

        return self.registered[name]

    @cached_property
    def registered(self):

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

        entrypoint_group = f"anemoi.{self.kind}"
        for entry_point in entrypoints.get_group_all(entrypoint_group):
            if entry_point.name in self._registered:
                LOG.warning(
                    f"Overwriting builtin '{entry_point.name}' from {self.package} with plugin '{entry_point.module_name}'"
                )
            self._registered[entry_point.name] = entry_point.load()

        return self._registered

    def create(self, name: str, *args, **kwargs):
        factory = self.lookup(name)
        return factory(*args, **kwargs)

    # def __call__(self, name: str, *args, **kwargs):
    #     return self.create(name, *args, **kwargs)

    def from_config(self, config, *args, **kwargs):
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
