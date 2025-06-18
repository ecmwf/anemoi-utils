from copy import deepcopy
from dataclasses import dataclass
from importlib.util import module_from_spec
from importlib.util import spec_from_file_location
from os import PathLike
from pathlib import Path
from typing import Any
from typing import Callable
from typing import List
from typing import MutableMapping
from typing import Sequence
from typing import Tuple
from typing import TypeAlias
from typing import Union

ckpt_migration_key = "ckpt-migrations"


class MissingMigrationFieldException(BaseException):
    pass


CkptType: TypeAlias = MutableMapping[str, Any]
MigrationCallback: TypeAlias = Callable[[CkptType], CkptType]


@dataclass
class Migration:
    name: str
    callback: MigrationCallback


def get_missing_migrations(ckpt: CkptType, migrations: Sequence[Migration]) -> List[Migration]:
    """Get missing migrations from a checkpoint"""
    if ckpt_migration_key not in ckpt:
        return list(migrations)
    done_migrations = ckpt[ckpt_migration_key]
    for k, mig in reversed(list(enumerate(migrations))):
        if mig.name in done_migrations:
            return list(migrations[k + 1 :])
    return list(migrations)


def _mark_ckpt(ckpt: CkptType, migration: Migration) -> CkptType:
    """Add migration fields to ckpt"""
    if ckpt_migration_key not in ckpt.keys():
        ckpt[ckpt_migration_key] = []
    ckpt[ckpt_migration_key].append(migration.name)
    return ckpt


def migrate_ckpt(
    ckpt: CkptType,
    migrations: Sequence[Migration],
) -> Tuple[CkptType, List[Migration]]:
    """Migrate checkpoint using provided migrations

    Parameters
    ----------
    ckpt : CkptType
        the checkpoint to migrate
    migrations : Sequence[Migration]
        The list of migrations to perform

    Returns
    -------
    Tuple[CkptType, List[Migration]]
        The migrated checkpoint and the list of migrations that were applied to the
        checkpoint
    """
    missing_migrations = get_missing_migrations(ckpt, migrations)
    for migration in missing_migrations:
        ckpt = migration.callback(deepcopy(ckpt))
        ckpt = _mark_ckpt(ckpt, migration)
    return ckpt, missing_migrations


def get_folder_migrations(path: Union[str, PathLike]) -> List[Migration]:
    migrations: List[Migration] = []

    for file in sorted(Path(path).iterdir()):
        if not file.is_file() and file.suffix != ".py":
            continue
        migration_spec = spec_from_file_location("migrate", file)
        if migration_spec is None or migration_spec.loader is None:
            continue
        migration_mod = module_from_spec(migration_spec)
        migration_spec.loader.exec_module(migration_mod)
        migrations.append(
            Migration(
                name=file.stem,
                callback=migration_mod.migrate,
            )
        )
    return migrations


def migrate_from_folder(ckpt: CkptType, path: Union[str, PathLike]) -> Tuple[CkptType, Sequence[Migration]]:
    return migrate_ckpt(ckpt, get_folder_migrations(path))
