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

import tomllib
from importlib import resources

import pytest
from pydantic import ValidationError

from anemoi.utils.settings import AnemoiSettings
from anemoi.utils.settings import copy_default_settings
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
