# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import Optional

from pydantic import FilePath

from .base import AnemoiBaseSettingsSchema


class ParamDBConfig(AnemoiBaseSettingsSchema):
    """Configuration for the GRIB parameter database lookups.

    Used by ``anemoi.utils.grib`` to control how GRIB parameter metadata
    is resolved (online API vs local cache, default origin for disambiguation,
    and cache lifetime).
    """

    default_origin: str = "ecmf"
    """Default origin to use when disambiguating parameters with the same shortname."""

    cache_length: int = 30
    """Cache length in days for GRIB parameter lookups."""

    local_cache: Optional[FilePath] = None
    """Path to a local JSON cache file for GRIB parameters. If set, used instead of the online API."""
