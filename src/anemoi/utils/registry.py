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


class Registry:
    """A registry of factories"""

    def __init__(self, package):

        self.package = package
        self.registered = {}
        self.kind = package.split(".")[-1]

    def register(self, name: str, factory: callable = None):

        if factory is None:
            return Wrapper(name, self)

        self.registered[name] = factory

    def _load(self, file):
        name, _ = os.path.splitext(file)
        try:
            importlib.import_module(f".{name}", package=self.package)
        except Exception:
            LOG.warning(f"Error loading filter '{self.package}.{name}'", exc_info=True)

    def lookup(self, name: str) -> callable:
        if name in self.registered:
            return self.registered[name]

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
            if entry_point.name == name:
                if name in self.registered:
                    LOG.warning(
                        f"Overwriting builtin '{name}' from {self.package} with plugin '{entry_point.module_name}'"
                    )
                self.registered[name] = entry_point.load()

        if name not in self.registered:
            raise ValueError(f"Cannot load '{name}' from {self.package}")

        return self.registered[name]

    def create(self, name: str, *args, **kwargs):
        factory = self.lookup(name)
        return factory(*args, **kwargs)

    def __call__(self, name: str, *args, **kwargs):
        return self.create(name, *args, **kwargs)
