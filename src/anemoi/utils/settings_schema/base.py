# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pydantic import BaseModel
from pydantic import ConfigDict


class AnemoiBaseSettingsSchema(BaseModel):
    """Base schema for Anemoi settings."""

    model_config = ConfigDict(
        extra="allow",
        alias_generator=lambda key: key.replace("_", "-"),
        serialize_by_alias=True,
        populate_by_name=True,
    )
