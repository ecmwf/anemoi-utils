# (C) Copyright 2026- Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import Optional

from pydantic import SecretStr

from .base import AnemoiBaseSettingsSchema


class RegistryConfig(AnemoiBaseSettingsSchema):
    """Configuration for access to the Anemoi registry."""

    api_url: str | None = None
    """API URL for the registry."""

    api_token: Optional[SecretStr] = None
    """API token for authenticating with the registry."""

    allow_delete: bool = False
    """Allow deletion operations in the registry."""

    plots_uri_pattern: str | None = None
    """URI pattern for plots storage."""

    datasets_uri_pattern: str | None = None
    """URI pattern for datasets storage."""

    weights_uri_pattern: str | None = None
    """URI pattern for weights storage."""

    weights_platform: str | None = None
    """Platform identifier for weights."""
