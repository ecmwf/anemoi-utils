# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import Optional

from .base import AnemoiBaseSettingsSchema


class UtilsConfig(AnemoiBaseSettingsSchema):
    """Miscellaneous anemoi-utils settings.

    Used by ``anemoi.utils.grids`` for custom grid file paths.
    """

    grids_path: Optional[str] = None
    """Custom path to a directory containing precomputed grid files (grid-<name>.npz).

    When set, grids are loaded from this directory before falling back to the
    built-in remote source. Supports ~ expansion.
    """
