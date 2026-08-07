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

from datetime import timedelta

from pymetkit import ParamDB

from .settings import AnemoiSettings

SETTINGS = AnemoiSettings()
"""Anemoi settings, loaded on module import."""

PARAMDB = ParamDB(
    mode=SETTINGS.paramdb.mode,
    cache_ttl=timedelta(days=SETTINGS.paramdb.cache_length),
    yaml_path=SETTINGS.paramdb.local_data,
)


def shortname_to_paramid(shortname: str, **filters) -> int:
    """Return the GRIB parameter id given its shortname.

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
    return PARAMDB.shortname_to_param_id(shortname, **filters)


def paramid_to_shortname(paramid: int, **filters) -> str:
    """Return the shortname of a GRIB parameter given its id.

    Parameters
    ----------
    paramid : int
        Parameter id.
    filters : Any
        Additional filters to disambiguate parameters with the same shortname (e.g. origin, access, table, discipline, category).

    Returns
    -------
    str
        Parameter shortname.

    >>> paramid_to_shortname(167)
    '2t'
    """
    return PARAMDB.param_id_to_shortname(paramid, **filters)  # type: ignore[reportReturnType]


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
    return PARAMDB.get_units(param)


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
