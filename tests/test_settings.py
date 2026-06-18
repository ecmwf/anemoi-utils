# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Tests for the pydantic-based settings system.

Validates that the bundled settings.defaults.toml is consistent with the
AnemoiSettings schema and that the copy_default_settings helper works.
"""

from __future__ import annotations

import os
import textwrap
import tomllib
from importlib import resources
from unittest.mock import patch

import pytest
from pydantic import SecretStr
from pydantic import ValidationError

import anemoi.utils.settings as settings_mod
from anemoi.utils.settings import AnemoiSettings
from anemoi.utils.settings import _collect_secret_paths
from anemoi.utils.settings import _split_secrets
from anemoi.utils.settings import convert_to_secret
from anemoi.utils.settings import copy_default_settings
from anemoi.utils.settings_schema.object_storage import ObjectStorageConfig
from anemoi.utils.settings_schema.paramdb import ParamDBConfig

# ---------------------------------------------------------------------------
# Locate the bundled defaults file
# ---------------------------------------------------------------------------

_DEFAULTS_TOML = resources.files("anemoi.utils.settings_schema") / "settings.defaults.toml"


def _load_defaults() -> dict:
    """Load the bundled defaults TOML as a plain dict."""
    with resources.as_file(_DEFAULTS_TOML) as p:
        return tomllib.loads(p.read_text())


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestDefaultSettingsAgainstSchema:
    """Ensure settings.defaults.toml is valid according to AnemoiSettings."""

    def test_defaults_toml_exists(self):
        """The bundled defaults file must be present in the package."""
        with resources.as_file(_DEFAULTS_TOML) as p:
            assert p.exists(), f"settings.defaults.toml not found at {p}"

    def test_defaults_is_valid_toml(self):
        """The file must parse as valid TOML."""
        data = _load_defaults()
        assert isinstance(data, dict)

    def test_defaults_validates_against_schema(self):
        """All sections/keys in the defaults file must pass schema validation."""
        data = _load_defaults()
        # AnemoiSettings uses aliases with hyphens (e.g. "object-storage"),
        # which is exactly how TOML sections are named.
        settings = AnemoiSettings(**data)
        assert settings is not None

    def test_all_schema_sections_present_in_defaults(self):
        """Every top-level field in the schema should have a section in defaults."""
        data = _load_defaults()
        schema_fields = set()
        for name, field in AnemoiSettings.model_fields.items():
            alias = field.alias or name
            schema_fields.add(alias)
        toml_sections = set(data.keys())
        missing = schema_fields - toml_sections
        assert not missing, f"Sections defined in schema but missing from defaults TOML: {missing}"

    def test_no_extra_sections_in_defaults(self):
        """The defaults file should not contain sections unknown to the schema."""
        data = _load_defaults()
        schema_fields = set()
        for name, field in AnemoiSettings.model_fields.items():
            alias = field.alias or name
            schema_fields.add(alias)
        toml_sections = set(data.keys())
        extra = toml_sections - schema_fields
        assert not extra, f"Sections in defaults TOML not defined in schema: {extra}"


# ---------------------------------------------------------------------------
# copy_default_settings tests
# ---------------------------------------------------------------------------


class TestSchemaRejectsInvalid:
    """Verify the schema catches invalid data — ensures tests are meaningful."""

    def test_unknown_top_level_section_is_ignored(self):
        """AnemoiSettings uses extra='ignore', so unknown top-level sections are silently dropped."""
        data = _load_defaults()
        data["totally_bogus_section"] = {"foo": "bar"}
        # Should NOT raise — extra='ignore' at the top level
        settings = AnemoiSettings(**data)
        assert not hasattr(settings, "totally_bogus_section")

    def test_wrong_type_for_known_field_raises(self):
        """Passing the wrong type for a schema field should raise ValidationError."""
        with pytest.raises(ValidationError):
            ParamDBConfig(cache_length="not-an-int")


class TestCopyDefaultSettings:
    """Tests for the copy_default_settings helper."""

    def test_copy_creates_file(self, tmp_path):
        """copy_default_settings should create the file at the destination."""
        dest = tmp_path / "settings.toml"
        result = copy_default_settings(dest)
        assert result == dest
        assert dest.exists()

    def test_copy_content_is_valid_toml(self, tmp_path):
        """The copied file should be valid TOML that parses."""
        dest = tmp_path / "settings.toml"
        copy_default_settings(dest)
        data = tomllib.loads(dest.read_text())
        assert isinstance(data, dict)
        assert "object-storage" in data

    def test_copy_no_overwrite_by_default(self, tmp_path):
        """When the file already exists, copy_default_settings should not overwrite."""
        dest = tmp_path / "settings.toml"
        dest.write_text("# existing\n")
        copy_default_settings(dest)
        assert dest.read_text() == "# existing\n"

    def test_copy_overwrite_when_requested(self, tmp_path):
        """With overwrite=True, the file should be replaced."""
        dest = tmp_path / "settings.toml"
        dest.write_text("# existing\n")
        copy_default_settings(dest, overwrite=True)
        content = dest.read_text()
        assert "object-storage" in content

    def test_copy_creates_parent_dirs(self, tmp_path):
        """Parent directories should be created automatically."""
        dest = tmp_path / "deeply" / "nested" / "settings.toml"
        copy_default_settings(dest)
        assert dest.exists()


# ---------------------------------------------------------------------------
# Fixture: isolated settings pointing at tmp_path config files
# ---------------------------------------------------------------------------


@pytest.fixture()
def isolated_settings(tmp_path, monkeypatch):
    """Point settings loading at a temporary directory.

    Returns a helper with .toml, .secrets_toml paths and a .load() that
    builds an AnemoiSettings from those files.
    """
    _config = tmp_path / "settings.toml"
    _secrets = tmp_path / "settings.secrets.toml"

    # Redirect the module-level location so all sources read from tmp_path
    monkeypatch.setattr(settings_mod, "ANEMOI_SETTINGS_FILE_LOCATION", _config)

    class _Ctx:
        toml = _config
        secrets_toml = _secrets

        @staticmethod
        def load(**env_overrides):
            """Build a fresh AnemoiSettings, optionally with env var overrides."""
            with patch.dict(os.environ, env_overrides, clear=False):
                return AnemoiSettings()

    return _Ctx()


# ---------------------------------------------------------------------------
# Settings loaded from TOML files
# ---------------------------------------------------------------------------


class TestSettingsFromFile:
    """Settings values are read from the config file."""

    def test_paramdb_default_origin_from_file(self, isolated_settings):
        """A value written to settings.toml is picked up."""
        isolated_settings.toml.write_text(textwrap.dedent("""\
                [paramdb]
                default_origin = "destine"
            """))
        s = isolated_settings.load()
        assert s.paramdb.default_origin == "destine"

    def test_datasets_path_from_file(self, isolated_settings):
        """A list field is loaded correctly from TOML."""
        isolated_settings.toml.write_text(textwrap.dedent("""\
                [datasets]
                path = ["/data/a", "/data/b"]
            """))
        s = isolated_settings.load()
        assert s.datasets.path == ["/data/a", "/data/b"]

    def test_missing_file_uses_defaults(self, isolated_settings):
        """When no config file exists, built-in defaults are used."""
        s = isolated_settings.load()
        assert s.paramdb.default_origin in ("ecmf")
        assert s.paramdb.cache_length == 30


# ---------------------------------------------------------------------------
# Environment variable overrides
# ---------------------------------------------------------------------------


class TestEnvVarOverrides:
    """Environment variables take precedence over file values."""

    def test_env_overrides_file_value(self, isolated_settings):
        """An env var should override the same key from the config file."""
        isolated_settings.toml.write_text(textwrap.dedent("""\
                [paramdb]
                default_origin = "ecmf"
            """))
        s = isolated_settings.load(ANEMOI_SETTINGS_PARAMDB__DEFAULT_ORIGIN="destine")
        assert s.paramdb.default_origin == "destine"

    def test_env_overrides_default(self, isolated_settings):
        """An env var should override a built-in default when no file exists."""
        s = isolated_settings.load(ANEMOI_SETTINGS_PARAMDB__CACHE_LENGTH="7")
        assert s.paramdb.cache_length == 7

    def test_nested_env_var_for_object_storage(self, isolated_settings):
        """Nested env vars with double-underscore separators should work."""
        s = isolated_settings.load(ANEMOI_SETTINGS_OBJECT_STORAGE__ENDPOINT_URL="https://custom.s3.example.com")
        assert s.object_storage.endpoint_url == "https://custom.s3.example.com"


# ---------------------------------------------------------------------------
# Secrets separation
# ---------------------------------------------------------------------------


class TestSecretsSeparation:
    """Secrets and non-secrets must live in separate files."""

    def test_secrets_loaded_from_secrets_file(self, isolated_settings):
        """SecretStr fields in the secrets file are loaded."""
        isolated_settings.secrets_toml.write_text(textwrap.dedent("""\
                [object-storage]
                access_key_id = "AKIAIOSFODNN7EXAMPLE"
                secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            """))
        isolated_settings.secrets_toml.chmod(0o600)
        s = isolated_settings.load()
        assert isinstance(s.object_storage.access_key_id, SecretStr)
        assert s.object_storage.access_key_id.get_secret_value() == "AKIAIOSFODNN7EXAMPLE"

    def test_secrets_in_config_file_are_rejected(self, isolated_settings):
        """Putting SecretStr fields in the main config file should raise."""
        isolated_settings.toml.write_text(textwrap.dedent("""\
                [object-storage]
                access_key_id = "AKIAIOSFODNN7EXAMPLE"
            """))
        with pytest.raises(ValueError, match="[Ss]ecret"):
            isolated_settings.load()

    def test_non_secrets_in_secrets_file_are_ignored(self, isolated_settings):
        """Non-secret keys in the secrets file should be silently ignored."""
        isolated_settings.secrets_toml.write_text(textwrap.dedent("""\
                [paramdb]
                default_origin = "should-be-ignored"

                [object-storage]
                access_key_id = "AKIAEXAMPLE"
            """))
        isolated_settings.secrets_toml.chmod(0o600)
        s = isolated_settings.load()
        # The non-secret key should NOT have been applied
        assert s.paramdb.default_origin != "should-be-ignored"


# ---------------------------------------------------------------------------
# File permissions enforcement
# ---------------------------------------------------------------------------


class TestSecretsFilePermissions:
    """Secrets files must have restrictive permissions (0600)."""

    @pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
    def test_secrets_file_with_wrong_permissions_raises(self, isolated_settings):
        """A secrets file readable by group/other should be rejected."""
        isolated_settings.secrets_toml.write_text(textwrap.dedent("""\
                [object-storage]
                access_key_id = "AKIAEXAMPLE"
            """))
        isolated_settings.secrets_toml.chmod(0o644)
        with pytest.raises(PermissionError, match="0o600"):
            isolated_settings.load()

    @pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
    def test_secrets_file_with_correct_permissions_loads(self, isolated_settings):
        """A secrets file with 0600 permissions should load normally."""
        isolated_settings.secrets_toml.write_text(textwrap.dedent("""\
                [object-storage]
                access_key_id = "AKIAEXAMPLE"
            """))
        isolated_settings.secrets_toml.chmod(0o600)
        s = isolated_settings.load()
        assert s.object_storage.access_key_id.get_secret_value() == "AKIAEXAMPLE"


# ---------------------------------------------------------------------------
# Source priority order
# ---------------------------------------------------------------------------


class TestSourcePriority:
    """Settings sources are applied in the documented priority order:
    env vars > secrets file > config file > defaults.
    """

    def test_env_beats_config_file(self, isolated_settings):
        """Env var wins over the same key in the TOML file."""
        isolated_settings.toml.write_text(textwrap.dedent("""\
                [paramdb]
                cache_length = 60
            """))
        s = isolated_settings.load(ANEMOI_SETTINGS_PARAMDB__CACHE_LENGTH="1")
        assert s.paramdb.cache_length == 1

    def test_config_file_beats_default(self, isolated_settings):
        """A file value wins over the built-in default."""
        isolated_settings.toml.write_text(textwrap.dedent("""\
                [paramdb]
                cache_length = 99
            """))
        s = isolated_settings.load()
        assert s.paramdb.cache_length == 99


# ---------------------------------------------------------------------------
# Hyphen / underscore alias handling
# ---------------------------------------------------------------------------


class TestAliasHandling:
    """Hyphens and underscores are interchangeable in settings keys."""

    def test_toml_uses_hyphens(self, isolated_settings):
        """TOML sections written with hyphens are loaded correctly."""
        isolated_settings.toml.write_text(textwrap.dedent("""\
                [object-storage]
                endpoint_url = "https://hyphen.example.com"
            """))
        s = isolated_settings.load()
        assert s.object_storage.endpoint_url == "https://hyphen.example.com"

    def test_serialisation_uses_hyphens(self, isolated_settings):
        """model_dump(by_alias=True) should produce hyphenated keys."""
        s = isolated_settings.load()
        dumped = s.model_dump(by_alias=True)
        assert "object-storage" in dumped
        assert "object_storage" not in dumped


# ---------------------------------------------------------------------------
# Per-bucket object storage overrides
# ---------------------------------------------------------------------------


class TestBucketOverrides:
    """Per-bucket S3 config overrides merge with global settings."""

    def test_bucket_override_applied(self, isolated_settings):
        """A bucket-specific endpoint should override the global one."""
        isolated_settings.toml.write_text(textwrap.dedent("""\
                [object-storage]
                endpoint_url = "https://global.example.com"

                [object-storage."my-bucket"]
                endpoint_url = "https://private.example.com"
                skip_signature = true
            """))
        s = isolated_settings.load()
        assert s.object_storage.endpoint_url == "https://global.example.com"
        bucket_cfg = getattr(s.object_storage, "my-bucket")
        assert bucket_cfg.endpoint_url == "https://private.example.com"
        assert bucket_cfg.skip_signature is True

    def test_bucket_override_inherits_global(self, isolated_settings):
        """A bucket override that omits a key should not affect the global value."""
        isolated_settings.toml.write_text(textwrap.dedent("""\
                [object-storage]
                endpoint_url = "https://global.example.com"

                [object-storage."other-bucket"]
                skip_signature = true
            """))
        s = isolated_settings.load()
        bucket_cfg = getattr(s.object_storage, "other-bucket")
        # The bucket config has its own fields; endpoint_url defaults to ""
        assert bucket_cfg.skip_signature is True
        # Global is untouched
        assert s.object_storage.endpoint_url == "https://global.example.com"


# ---------------------------------------------------------------------------
# Secret tree detection and splitting
# ---------------------------------------------------------------------------


class TestSecretTreeLogic:
    """The secret/non-secret partitioning correctly identifies SecretStr fields."""

    def test_object_storage_secrets_detected(self):
        """access_key_id and secret_access_key should be identified as secrets."""
        tree = _collect_secret_paths(ObjectStorageConfig)
        assert "access_key_id" in tree
        assert "secret_access_key" in tree

    def test_paramdb_has_no_secrets(self):
        """ParamDBConfig has no SecretStr fields."""
        tree = _collect_secret_paths(ParamDBConfig)
        assert tree == {}

    def test_split_separates_correctly(self):
        """_split_secrets should partition a dict based on the secret tree."""
        tree = _collect_secret_paths(ObjectStorageConfig)
        data = {
            "endpoint_url": "https://example.com",
            "access_key_id": "AKIA...",
            "secret_access_key": "wJal...",
        }
        secret, rest = _split_secrets(data, tree)
        assert "access_key_id" in secret
        assert "secret_access_key" in secret
        assert "endpoint_url" in rest
        assert "endpoint_url" not in secret

    def test_convert_to_secret_wraps_strings(self):
        """convert_to_secret should wrap plain strings as SecretStr."""
        result = convert_to_secret("my-key")
        assert isinstance(result, SecretStr)
        assert result.get_secret_value() == "my-key"

    def test_convert_to_secret_wraps_nested_dict(self):
        """convert_to_secret should recursively wrap dict values."""
        result = convert_to_secret({"a": "x", "b": "y"})
        assert isinstance(result["a"], SecretStr)
        assert result["b"].get_secret_value() == "y"


# ---------------------------------------------------------------------------
# reload_settings
# ---------------------------------------------------------------------------


class TestReloadSettings:
    """The global SETTINGS singleton can be refreshed."""

    def test_reload_picks_up_changes(self, isolated_settings, monkeypatch):
        """After writing a new config and calling reload_settings, the global changes."""
        from anemoi.utils.settings import reload_settings

        isolated_settings.toml.write_text(textwrap.dedent("""\
                [paramdb]
                cache_length = 42
            """))
        reload_settings()

        from anemoi.utils.settings import SETTINGS as reloaded

        assert reloaded.paramdb.cache_length == 42

        # Clean up: reload again without the file to restore defaults
        isolated_settings.toml.unlink(missing_ok=True)
        reload_settings()
