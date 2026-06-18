# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from .base import AnemoiBaseSettingsSchema


class DatasetsNamedConfig(BaseModel):
    """Named dataset mappings (friendly name -> full path/URL)."""

    __pydantic_extra__: dict[str, Any]

    model_config = ConfigDict(extra="allow")


class DatasetsConfig(AnemoiBaseSettingsSchema):
    """Configuration for dataset discovery and validation.

    Used by ``anemoi-datasets`` for search paths, naming convention checks,
    and named dataset aliases.
    """

    path: list[str] = Field(default_factory=list)
    """Search paths: list of directories or S3 prefixes for .zarr dataset lookup."""

    use_search_path_not_found: bool = False
    """When true, if a .zarr path does not exist, strip to basename and search the paths above instead of failing immediately."""

    ignore_naming_conventions: bool = False
    """When true, skip all dataset naming-convention validation during creation."""

    named: DatasetsNamedConfig = Field(default_factory=DatasetsNamedConfig)
    """Map of friendly dataset names to full paths or URLs."""
