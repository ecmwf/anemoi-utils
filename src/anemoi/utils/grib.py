# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Utilities for working with GRIB parameters.

Aliases Pymetkit's ParamDB to provide a consistent interface for GRIB parameter lookups across Anemoi, with configuration controlled by Anemoi settings.
Use `PARAMDB` for direct access.

See https://codes.ecmwf.int/grib/param-db/ for more information.
"""

import logging
from datetime import timedelta
from functools import cache
from typing import Any

from pymetkit import ParamDB

from .settings import SETTINGS

"""Anemoi settings, loaded on module import."""

PARAMDB_SETTINGS = SETTINGS.paramdb
LOG = logging.getLogger(__name__)


@cache
def get_paramdb() -> ParamDB:
    """Return the global ParamDB instance.

    Returns
    -------
    ParamDB
        The global ParamDB instance.
    """

    return ParamDB(
        mode=PARAMDB_SETTINGS.mode,
        cache_path=PARAMDB_SETTINGS.cache_path,
        cache_ttl=timedelta(days=PARAMDB_SETTINGS.cache_length),
        yaml_path=PARAMDB_SETTINGS.local_data,
    )


def shortname_to_paramid(shortname: str, **filters: Any) -> int:
    """Return the GRIB parameter id given its shortname.

    SETTINGS.paramdb.default_filters can be used to provide default filters for disambiguation.

    If a collision is detected (i.e. multiple parameters with the same shortname), a warning will be logged and the first parameter id will be returned.
    Additional filters can be provided to disambiguate.

    Parameters
    ----------
    shortname : str
        Parameter shortname.
    filters : Any
        Additional filters to disambiguate parameters with the same shortname (e.g. origin, access, table).

    Returns
    -------
    int
        Parameter id.

    >>> shortname_to_paramid("2t")
    167
    """
    filters = filters or PARAMDB_SETTINGS.default_filters or {}

    if get_paramdb().shortname_has_collisions(shortname) and not filters:
        candidates = get_paramdb().shortname_to_param_id_candidates(shortname)
        log_message = (
            f"Shortname '{shortname}' has collisions. Candidates: {[c.param_id for c in candidates]}. "
            "Consider providing additional filters to disambiguate, will use empty context by default."
            f"\nTo select one of the ids use: \n"
            + "\n".join(
                f"  - {c.param_id}: {f'context = {c.mars_request_context}' if c.mars_request_context is not None else c.hard_filter_selector}"
                for c in candidates
            )
        )
        LOG.warning(log_message)
        filters = {"context": {}}
    return get_paramdb().shortname_to_param_id(shortname, **filters)


def paramid_to_shortname(paramid: int) -> str:
    """Return the shortname of a GRIB parameter given its id.

    Parameters
    ----------
    paramid : int
        Parameter id.

    Returns
    -------
    str
        Parameter shortname.

    >>> paramid_to_shortname(167)
    '2t'
    """
    return get_paramdb().param_id_to_shortname(paramid)


def units(param: int | str) -> str:
    """Return the units of a GRIB parameter given its name or id.

    Parameters
    ----------
    param : int or str
        Parameter id or name.

    Returns
    -------
    str
        Parameter unit.

    >>> units(167)
    'K'
    """
    return get_paramdb().get_units(param)


def must_be_positive(param: int | str) -> bool:
    """Check if a parameter must be positive.

    Parameters
    ----------
    param : int or str
        Parameter id or shortname.

    Returns
    -------
    bool
        True if the parameter must be positive.

    >>> must_be_positive("tp")
    True
    """
    return units(param) in ["m", "kg kg**-1", "m of water equivalent"]
