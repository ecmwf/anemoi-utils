# (C) Copyright 2025-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from __future__ import annotations

import importlib
import importlib.util
import logging
import subprocess
import sys
from abc import ABC
from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from os import PathLike
from pathlib import Path
from types import ModuleType
from typing import Any
from typing import Generic
from typing import Protocol
from typing import Self
from typing import TypedDict
from typing import TypeVar

LOGGER = logging.getLogger(__name__)


class IncompleteMigrationScript(BaseException):
    """The migration script is missing some mandatory content (metadata)."""


def get_migration_name(name: str) -> str:
    """Returns the migration full name from a given name.

    Parameters
    ----------
    name : str
        The chosen name.

    Returns
    -------
    str
        The full name with a timestamp and chosen name.
    """

    name = name.lower().replace("-", "_").replace(" ", "_")
    now = int(datetime.now(UTC).timestamp())
    return f"{now}_{name}.py"


def added_migrations_compared_to_main_branch(root_folder: Path, migration_path: Path) -> list[str]:
    """Finds the all now migration scripts that were added compared to origin/main.

    Parameters
    ----------
    root_folder : Path
        Path to the root folder of the project (the path to ./src).
    migration_path : Path
        Path to the migration script folder.

    Returns
    -------
    list[str]
        The list of added migration in this branch compared to origin/main.
    """
    run_new_migrations = subprocess.run(
        "git diff --name-only --diff-filter=A "
        '$(git log -n 1 origin/main --pretty=format:"%H") '
        f"HEAD {migration_path.resolve()}",
        check=True,
        capture_output=True,
        shell=True,
    )
    new_migrations = [root_folder / file for file in run_new_migrations.stdout.decode("utf-8").split("\n")]
    new_migrations = [file.name for file in new_migrations if file.is_file() and file.name != "__init__.py"]
    return sorted(new_migrations)


def migrations_in_incorrect_order(all_migrations: list[str], new_migrations: list[str]) -> tuple[list[str], str | None]:
    """Tests whether the order of the new migrations is correct.

    All new migrations should be at the end of all_migrations.

    Parameters
    ----------
    all_migrations : list[str]
        All migrations currently in anemoi-models.
    new_migrations : list[str]
        New migrations from this PR.

    Returns
    -------
    tuple[list[str], str | None]
        * The list of name in incorrect order,
        * the name of the last migration in main.
    """
    stop_new = False
    incorrect_order: list[str] = []
    last_name: str | None = None

    for name in reversed(all_migrations):
        if name not in new_migrations and not stop_new:
            stop_new = True
            last_name = name
        elif stop_new and name in new_migrations:
            incorrect_order.append(name)
    return list(reversed(incorrect_order)), last_name


_Version = TypeVar("_Version")


@dataclass
class MigrationMetadata(Generic[_Version]):
    """Metadata object of the migration."""

    versions: _Version
    """ Migration and anemoi-model versions. """
    final: bool = False
    """ Whether the migration is final."""


class SerializedMigration(TypedDict, Generic[_Version]):
    """The serialized migration stored in the checkpoint"""

    name: str
    """ Name of the migration """
    metadata: MigrationMetadata[_Version]
    signature: str
    """ The signature of the script. Can be used to detect if a script changed. """


_T = TypeVar("_T")
_U = TypeVar("_U")


class Migration(ABC, Generic[_T, _U, _Version]):
    """Represents a migration"""

    def __init__(
        self,
        name: str,
        metadata: MigrationMetadata[_Version],
        signature: str,
        migrate: Callable[[_T], _U] | None = None,
    ) -> None:
        self._name = name
        self._metadata = metadata
        self._signature = signature
        self._migrate = migrate

    @classmethod
    @abstractmethod
    def from_migration(cls, name: str, migration: ModuleType) -> Self: ...

    @property
    def name(self) -> str:
        """Name of the migration"""
        return self._name

    @property
    def metadata(self) -> MigrationMetadata[_Version]:
        """Tracked metadata"""
        return self._metadata

    @property
    def signature(self) -> str:
        """Signature of the migration. Can be used to detect if the script changed"""
        return self._signature

    @property
    def migrate(self) -> Callable[[_T], _U] | None:
        """Callback to execute the migration"""
        return self._migrate

    def serialize(self) -> SerializedMigration[_Version]:
        """Serialize this migration

        Returns
        -------
        SerializedMigration
            The serialized dict to store in the checkpoint.
        """

        return {
            "name": self.name,
            "metadata": self.metadata,
            "signature": self.signature,
        }


class ObjType(Protocol):
    def __contains__(self, x: Any, /) -> bool: ...
    def __getitem__(self, key: Any, /) -> Any: ...


def _import_file(location: Path, package: str | None = None) -> ModuleType:
    """Import a module from a file path.

    Parameters
    ----------
    location : Path
        Path to the Python file
    package : str | None
        Optional package context for namespacing in sys.modules

    Returns
    -------
    ModuleType
        The imported module
    """
    spec = importlib.util.spec_from_file_location(location.stem, location)
    if spec is None or spec.loader is None:
        raise ValueError(f"{location} does not point to a valid Python file.")

    module = importlib.util.module_from_spec(spec)

    module_name = f"{package}.{location.stem}" if package else location.stem
    sys.modules[module_name] = module

    spec.loader.exec_module(module)
    return module


_M = TypeVar("_M", bound=Migration)
_O = TypeVar("_O", bound=ObjType)


def _is_valid_migration_file(file: Path) -> bool:
    return file.is_file() and file.suffix == ".py" and file.name != "__init__.py"


class Migrator(ABC, Generic[_M, _O]):
    def __init__(self, migrations: Sequence[_M], obj_migration_key: str) -> None:
        """Create the migrator object

        Parameters
        ----------
        migrations : Sequence[Migration]
            List of migration to execute. If None, get migrations from the current folder.
        obj_migration_key : str
            Key in the object that contain the migrations to infer the current migration
            state of the object.
        """

        self._obj_migration_key = obj_migration_key

        # Migratable objects can only be migrated within its compatibility group.
        # Compatibility groups are separated by "final" migrations.
        # The object only tracks the migrations from within its group.
        self._compatibility_groups: list[list[_M]] = []
        self._migration_refs: dict[str, int] = {}
        self._migration_groups: dict[str, int] = {}
        current_group: list[_M] = []
        for migration in migrations:
            LOGGER.info("Loading migration %s.", migration.name)
            if migration.metadata.final:
                self._compatibility_groups.append(current_group)
                current_group = []
            self._migration_refs[migration.name] = len(current_group)
            self._migration_groups[migration.name] = len(self._compatibility_groups)
            current_group.append(migration)
        self._compatibility_groups.append(current_group)

    @classmethod
    def _migrations_from_files(cls, migration_type: type[_M], locations: Iterable[Path], package: str) -> list[_M]:
        """Returns the migrations from a given folder.

        Parameters
        ----------
        migration_type : type[_M]
            The migration type.
        locations : Iterable[Path]
            Paths to the migration file to load. They must be sorted in migration order.
        package : str
            Reference package for the import of the migrations.

        Returns
        -------
        list[Migration]
            The migrations from the given path
        """
        migrations: list[_M] = []

        for file in locations:
            LOGGER.debug("Loading migration file .%s from %s.", file.stem, package)
            migration = _import_file(file, package)
            migrations.append(migration_type.from_migration(file.stem, migration))
        return migrations

    @classmethod
    def _migrations_from_path(cls, migration_type: type[_M], location: str | PathLike, package: str) -> list[_M]:
        files = sorted(filter(_is_valid_migration_file, Path(location).iterdir()))
        return cls._migrations_from_files(migration_type, files, package)

    @classmethod
    def from_path(
        cls, migration_type: type[_M], location: str | PathLike, package: str, obj_migration_key: str
    ) -> Self:
        """Load from a given folder.

        Parameters
        ----------
        migration_type : type[_M]
            The type of the Migration object to use.
        location : str | PathLike
            Path to the migration folder.
        package : str
            Reference package for the import of the migrations.
        obj_migration_key : str
            Key in the object that contain the migrations to infer the current migration
            state of the object.

        Returns
        -------
        Self
            A Migrator instance.
        """
        return cls(cls._migrations_from_path(migration_type, location, package), obj_migration_key)

    @abstractmethod
    def _current_group(self, obj: _O) -> int:
        """Returns the current index of the object's compatibility group."""

    def is_compatible(self, obj: _O) -> bool:
        """Checks whether the object is compatible with the current version.

        Parameters
        ----------
        obj : _T
            The object

        Returns
        -------
        bool
            Whether it is compatible
        """
        # No migration means checkpoint too old, no migrations available.
        if self._obj_migration_key not in obj:
            return False
        # If empty, means first group
        if not len(obj[self._obj_migration_key]):
            return not len(self._compatibility_groups) > 1

        obj_compat_group = self._current_group(obj)
        return obj_compat_group == len(self._compatibility_groups) - 1
