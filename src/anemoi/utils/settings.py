# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging
import os
import shutil
from importlib import resources
from pathlib import Path
from typing import Any
from typing import get_args
from typing import get_origin
from typing import get_type_hints
from typing import overload

from pydantic import BaseModel
from pydantic import Field
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import PydanticBaseSettingsSource
from pydantic_settings import SettingsConfigDict
from pydantic_settings import TomlConfigSettingsSource
from pydantic_settings import YamlConfigSettingsSource

from anemoi.utils.config import LOG

from .settings_schema.datasets import DatasetsConfig
from .settings_schema.object_storage import ObjectStorageConfig
from .settings_schema.paramdb import ParamDBConfig
from .settings_schema.registry import RegistryConfig
from .settings_schema.utils import UtilsConfig

logger = logging.getLogger(__name__)

ANEMOI_SETTINGS_FILE_LOCATION = Path(
    os.getenv("ANEMOI_SETTINGS_FILE", Path.home() / ".config" / "anemoi" / "settings.toml")
).with_suffix(".toml")
_SECRETS_FILE_MODE = 0o600

# Path to the bundled defaults file shipped with the package
_DEFAULTS_RESOURCE = resources.files("anemoi.utils.settings_schema") / "settings.defaults.toml"


def copy_default_settings(dest: Path | None = None, *, overwrite: bool = False) -> Path:
    """Copy the bundled ``settings.defaults.toml`` to the user default settings location.

    Parameters
    ----------
    dest : Path, optional
        Custom destination path for the copied defaults file. If None (default), uses the standard user config location (~/.config/anemoi/settings.defaults.toml).
    overwrite : bool
        If *False* (default), skip the copy when the destination file already exists.

    Returns
    -------
    Path
        The path the file was (or would have been) written to.
    """
    if dest is None:
        dest = Path.home() / ".config" / "anemoi" / "settings.defaults.toml"

    if dest.exists() and not overwrite:
        logger.debug("Settings file already exists at %s — skipping copy.", dest)
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)

    # importlib.resources gives us a Traversable; copy it out to the real path
    with resources.as_file(_DEFAULTS_RESOURCE) as src:
        shutil.copy2(src, dest)

    logger.info("Copied default settings to %s", dest)
    return dest


def _ensure_secure_file(path: Path) -> None:
    """Verify a secrets file is not world/group readable (POSIX only)."""
    if os.name != "posix" or not path.exists():
        return
    mode = path.stat().st_mode & 0o777
    if mode != _SECRETS_FILE_MODE:
        raise PermissionError(
            f"Secrets file {path} must have permissions {oct(_SECRETS_FILE_MODE)}; got {oct(mode)}. "
            f"Run: chmod 600 {path}"
        )


_WILDCARD = "*"
# A SecretTree is a nested dict where leaves are True (SecretStr) and inner
# nodes are sub-trees keyed by underscore-normalised field name. The special
# key "*" represents typed extras (`__pydantic_extra__: dict[str, Model]`).
SecretTree = dict[str, Any]
# A DataTree mirrors the shape of the input data: a nested dict with arbitrary
# leaf values, partitioned by `_split_secrets` according to a SecretTree.
DataTree = dict[str, Any]


def _resolve_annotation(ann: Any, seen: frozenset[type]) -> Any:
    """Return a SecretTree node for *ann*, or None if it carries no secrets."""
    candidates: list[Any] = [ann]
    if get_origin(ann) is not None:
        candidates.extend(a for a in get_args(ann) if a is not type(None))
    for t in candidates:
        if t is SecretStr:
            return True
        if isinstance(t, type) and issubclass(t, BaseModel):
            sub = _collect_secret_paths(t, seen)
            if sub:
                return sub
        if get_origin(t) is dict:
            args = get_args(t)
            if len(args) == 2:
                inner = _resolve_annotation(args[1], seen)
                if inner is not None:
                    return {_WILDCARD: inner}
    return None


def _collect_secret_paths(model_cls: type, seen: frozenset[type] = frozenset()) -> SecretTree:
    """Build a path-aware tree of SecretStr leaves for *model_cls*."""
    if not (isinstance(model_cls, type) and issubclass(model_cls, BaseModel)) or model_cls in seen:
        return {}
    seen = seen | {model_cls}
    tree: SecretTree = {}
    for name, field in model_cls.model_fields.items():
        node = _resolve_annotation(field.annotation, seen)
        if node is not None:
            tree[name.replace("-", "_")] = node
    # Typed extras: `__pydantic_extra__: dict[str, SubModel]`
    try:
        hints = get_type_hints(model_cls)
    except Exception:
        hints = {}
    extra_ann = hints.get("__pydantic_extra__")
    if extra_ann is not None:
        node = _resolve_annotation(extra_ann, seen)
        if isinstance(node, dict) and _WILDCARD in node:
            tree[_WILDCARD] = node[_WILDCARD]
        elif node is True:
            tree[_WILDCARD] = True
    return tree


def _flatten_tree(d: DataTree, prefix: str = "") -> list[str]:
    """Flatten a DataTree into a list of dotted path strings."""
    out: list[str] = []
    for k, v in d.items():
        path = f"{prefix}{k}"
        if isinstance(v, dict):
            out.extend(_flatten_tree(v, path + "."))
        else:
            out.append(path)
    return out


def _split_secrets(data: DataTree, tree: SecretTree) -> tuple[DataTree, DataTree]:
    """Partition *data* into (secret_part, non_secret_part) using *tree*."""
    secret: DataTree = {}
    rest: DataTree = {}
    for k, v in data.items():
        node = tree.get(k.replace("-", "_"), tree.get(_WILDCARD))
        if node is True:
            secret[k] = v
        elif isinstance(node, dict) and isinstance(v, dict):
            s, r = _split_secrets(v, node)
            if s:
                secret[k] = s
            if r:
                rest[k] = r
        else:
            rest[k] = v
    return secret, rest


@overload
def convert_to_secret(val: dict[str, str | Any]) -> dict[str, SecretStr | Any]: ...
@overload
def convert_to_secret(val: str) -> SecretStr: ...


def convert_to_secret(
    val: dict[str, str | Any] | str,
) -> dict[str, SecretStr | Any] | SecretStr:
    if isinstance(val, dict):
        return {k: convert_to_secret(v) for k, v in val.items()}
    elif isinstance(val, str):
        return SecretStr(val)
    elif isinstance(val, SecretStr):
        return val
    raise ValueError(f"Unsupported type for secret value: {type(val)}")


class AnemoiSecretsSource(PydanticBaseSettingsSource):
    """Loads SecretStr-typed fields from secured TOML/YAML files."""

    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        self._toml_path = ANEMOI_SETTINGS_FILE_LOCATION.with_suffix(".secrets.toml")
        self._yaml_path = ANEMOI_SETTINGS_FILE_LOCATION.with_suffix(".secrets.yaml")

        _ensure_secure_file(self._toml_path)
        _ensure_secure_file(self._yaml_path)

        self._toml_source = TomlConfigSettingsSource(settings_cls, toml_file=self._toml_path)
        self._yaml_source = YamlConfigSettingsSource(settings_cls, yaml_file=self._yaml_path)
        self._secret_tree = _collect_secret_paths(settings_cls)

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        raise NotImplementedError

    def __call__(self) -> dict[str, Any]:
        data: dict[str, Any] = {**self._yaml_source(), **self._toml_source()}
        if not data:
            return {}
        secret, rest = _split_secrets(data, self._secret_tree)
        if rest:
            logger.warning(
                "Ignoring non-secret keys in secrets file(s): %s. Move these to %s.",
                sorted(_flatten_tree(rest)),
                self._toml_path.with_name(self._toml_path.name.replace(".secrets", "")),
            )
        return convert_to_secret(secret) if secret else {}


class AnemoiNonSecretsSource(PydanticBaseSettingsSource):
    """Loads non-secret fields from TOML/YAML files; rejects any SecretStr leaves."""

    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        self._toml_source = TomlConfigSettingsSource(
            settings_cls,
            toml_file=ANEMOI_SETTINGS_FILE_LOCATION.with_suffix(".toml"),
        )
        self._yaml_source = YamlConfigSettingsSource(
            settings_cls,
            yaml_file=ANEMOI_SETTINGS_FILE_LOCATION.with_suffix(".yaml"),
        )
        self._secret_tree = _collect_secret_paths(settings_cls)

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        raise NotImplementedError

    def __call__(self) -> dict[str, Any]:
        data: dict[str, Any] = {**self._yaml_source(), **self._toml_source()}
        if not data:
            return {}
        secret, rest = _split_secrets(data, self._secret_tree)
        if secret:
            stem = ANEMOI_SETTINGS_FILE_LOCATION.stem
            raise ValueError(
                f"Secret keys {sorted(_flatten_tree(secret))} found in non-secret config files; "
                f"move them to the {stem}.secrets.toml/{stem}.secrets.yaml file (mode 0600)."
            )
        return rest


class AnemoiSettings(BaseSettings):
    """Settings for Anemoi.

    Use the ``ANEMOI_SETTINGS_FILE`` environment variable to specify a custom
    location for the main settings file
    (default: ``~/.config/anemoi/settings.toml``).

    The main settings file can be in either TOML or YAML format; the extension
    is ignored.  ``SecretStr``-typed fields should be placed in a separate
    secrets file with the same name but suffixed with ``.secrets``
    (e.g. ``settings.secrets.toml``) and must have permissions set to ``0600``.
    Non-secret fields will be ignored if found in the secrets file, and secret
    fields will be rejected if found in the main settings file, to encourage
    proper separation of concerns.

    **Note:** Init kwargs are intentionally disabled as a source of settings.

    Settings are loaded with the following priority (highest to lowest):

    1. Environment variables (with prefix ``ANEMOI_SETTINGS_`` and keys in
       upper case with underscores)
    2. Secret values from the ``.secrets.(toml|yaml)`` file
    3. Non-secret values from the ``.(toml|yaml)`` file
    4. Default values defined in the ``AnemoiSettings`` class and its nested
       models
    """

    model_config = SettingsConfigDict(
        env_prefix="ANEMOI_SETTINGS_",
        env_nested_delimiter="__",
        extra="ignore",
        alias_generator=lambda key: key.replace("_", "-"),
        serialize_by_alias=True,
        populate_by_name=True,
    )

    ## ---------- Setting fields ---------- ##

    object_storage: ObjectStorageConfig = Field(default_factory=ObjectStorageConfig, alias="object-storage")
    """Configuration for S3-compatible object storage."""

    datasets: DatasetsConfig = Field(default_factory=DatasetsConfig)
    """Dataset discovery and validation settings."""

    paramdb: ParamDBConfig = Field(default_factory=ParamDBConfig)
    """GRIB parameter database lookup settings."""

    registry: RegistryConfig = Field(default_factory=RegistryConfig)
    """Configuration for access to the Anemoi registry."""

    utils: UtilsConfig = Field(default_factory=UtilsConfig)
    """Miscellaneous anemoi-utils settings."""

    ## ---------- Control how the settings are loaded from various sources ---------- ##
    ## Priority order (highest to lowest): env vars > .env file > .secrets.(toml|yaml) > .(toml|yaml) > defaults in code ##

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            # init_settings, # Disable init kwargs to enforce separation of secrets/non-secrets and encourage use of env vars for overrides
            env_settings,
            dotenv_settings,
            AnemoiSecretsSource(settings_cls),
            AnemoiNonSecretsSource(settings_cls),
        )


SETTINGS = AnemoiSettings()
"""Global instance of the AnemoiSettings. This will be created on first import of the anemoi.utils.settings module, and can be reloaded with `reload_settings()`.

Use `AnemoiSettings()` to create separate instances if needed, but these will be runtime specific.
"""

try:
    copy_default_settings()  # Ensure the defaults file is present on disk for users to copy from
except Exception as e:
    LOG.warning(f"Failed to copy default settings: {e}")


def reload_settings():
    """Reload the Anemoi settings.

    Is run in-place on the global SETTINGS instance.
    """
    global SETTINGS
    SETTINGS = AnemoiSettings()
