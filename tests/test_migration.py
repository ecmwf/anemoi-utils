# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from collections.abc import MutableMapping
from pathlib import Path
from types import ModuleType
from typing import Any
from typing import Self
from typing import TypedDict

import pytest

from anemoi.utils.migrations import IncompleteMigrationScriptError
from anemoi.utils.migrations import Migration
from anemoi.utils.migrations import MigrationMetadata
from anemoi.utils.migrations import Migrator
from anemoi.utils.migrations import ObjectHasExtraMigrationsError
from anemoi.utils.migrations import ObjectMissingOlderMigrationsError
from anemoi.utils.migrations import ObjectTooOldError


class DummyMigrationVersions(TypedDict):
    migration: str


ObjType = MutableMapping[str, Any]


class DummyMigration(Migration[ObjType, ObjType, DummyMigrationVersions]):
    @classmethod
    def from_migration(cls, name: str, migration: ModuleType) -> Self:
        if not hasattr(migration, "metadata") or not isinstance(migration.metadata, MigrationMetadata):
            raise IncompleteMigrationScriptError("Migration script is missing metadata.")

        migrate = getattr(migration, "migrate", None)
        return cls(name, migration.metadata, name, migrate)

    @property
    def migration_state_key(self) -> str:
        """Key to use for the migration state."""
        return self.name


class DummyMigrator(Migrator[DummyMigration, ObjType]):
    def _migration_state(self, obj: ObjType) -> list[str] | None:
        if self._obj_migration_key not in obj:
            return None
        return obj[self._obj_migration_key]


class MigrationFactory:
    def __init__(self) -> None:
        self._counter = 0

    def count(self) -> int:
        counter = self._counter
        self._counter += 1
        return counter

    def make(self, amount: int, final: bool = False) -> list[DummyMigration]:
        migrations: list[DummyMigration] = []
        for _ in range(amount):
            # In the for-loop to make all migrate func different.
            def migrate(obj):
                return obj

            migrations.append(
                DummyMigration(
                    f"migration-{self.count()}",
                    MigrationMetadata(versions=DummyMigrationVersions(migration="1.0.0"), final=final),
                    f"migration-{self.count()}",
                    migrate,
                )
            )
        return migrations


@pytest.fixture
def migration_factory() -> MigrationFactory:
    return MigrationFactory()


HERE = Path(__file__).parent


def test_making_migrations_from_path() -> None:
    migration_files = HERE / "migrations"
    migrations = DummyMigrator._migrations_from_path(DummyMigration, migration_files, "tests.migrations")
    assert len(migrations) == 2
    assert migrations[0].name == "0_migrations-1"


def test_making_migrations_from_missing_path(tmpdir: Path) -> None:
    migration_files = tmpdir / "migrations"  # test for path that does not exist
    migrations = DummyMigrator._migrations_from_path(DummyMigration, migration_files, "tests.migrations")
    assert len(migrations) == 0


def test_missing_older_migration(migration_factory: MigrationFactory) -> None:
    migrations = migration_factory.make(amount=3)
    migrator = DummyMigrator(migrations, "migrations")

    obj_fully_migrated = {"migrations": [migration.name for migration in migrations]}
    missing_migrations = migrator.missing_older_migrations(obj_fully_migrated)
    assert len(missing_migrations) == 0

    # missing_older_migrations should only return missing migrations that are not at the end.
    # i.e. a missing migration in between other migrations.
    obj_missing_end_migration = {"migrations": [migration.name for migration in migrations[:-1]]}
    missing_migrations = migrator.missing_older_migrations(obj_missing_end_migration)
    assert len(missing_migrations) == 0

    obj_missing_middle_migration = {"migrations": [migrations[0].name, migrations[2].name]}
    missing_migrations = migrator.missing_older_migrations(obj_missing_middle_migration)
    assert len(missing_migrations) == 1
    assert missing_migrations[0] == migrations[1]


def test_fail_if_not_migratable_too_old(migration_factory: MigrationFactory) -> None:
    migrations = [
        *migration_factory.make(amount=1),
        *migration_factory.make(amount=1, final=True),
        *migration_factory.make(amount=2),
    ]
    migrator = DummyMigrator(migrations, "migrations")
    obj_too_old = {"migrations": [migrations[0].name]}
    with pytest.raises(ObjectTooOldError):
        migrator.fail_if_not_migratable(obj_too_old)


def test_fail_if_not_migratable_missing_older(migration_factory: MigrationFactory) -> None:
    migrations = migration_factory.make(amount=3)
    migrator = DummyMigrator(migrations, "migrations")
    obj_missing_older_migrations = {"migrations": [migrations[0].name, migrations[2].name]}
    with pytest.raises(ObjectMissingOlderMigrationsError):
        migrator.fail_if_not_migratable(obj_missing_older_migrations)


def test_fail_if_not_migratable_extra_migrations(migration_factory: MigrationFactory) -> None:
    migrations = migration_factory.make(amount=2)
    extra_migration = migration_factory.make(amount=1)[0]
    migrator = DummyMigrator(migrations, "migrations")
    obj_extra_migration_last = {"migrations": [*migrations, extra_migration.name]}
    with pytest.raises(ObjectHasExtraMigrationsError):
        migrator.fail_if_not_migratable(obj_extra_migration_last)

    obj_extra_migration_middle = {"migrations": [migrations[0].name, extra_migration.name, migrations[1].name]}
    with pytest.raises(ObjectHasExtraMigrationsError):
        migrator.fail_if_not_migratable(obj_extra_migration_middle)
