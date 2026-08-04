# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Utilities for working with GRIB parameters.

See https://codes.ecmwf.int/grib/param-db/ for more information.
"""

import json
import logging
import os
import re
import warnings
from functools import cache

import requests

from .caching import cached
from .settings import AnemoiSettings

LOG = logging.getLogger(__name__)

SETTINGS = AnemoiSettings()
"""Anemoi settings, loaded on module import."""


@cached(collection="grib", expires=SETTINGS.paramdb.cache_length * 24 * 3600)
def _units() -> dict[str, str]:
    """Fetch and cache GRIB parameter units.

    Returns
    -------
    dict
        A dictionary mapping unit ids to their names.
    """
    r = requests.get("https://codes.ecmwf.int/parameter-database/api/v1/unit/")
    r.raise_for_status()
    units = r.json()
    return {str(u["id"]): u["name"] for u in units}


@cache
def _get_local_db(local_db: str) -> list[dict[str, str | int | list[str]]]:
    """Open the local GRIB parameter database.

    Parameters
    ----------
    local_db : str
        Path to the local cache file.

    Returns
    -------
    list[dict[str, str | int | list[str]]]
        A list of dictionaries containing parameter details.

    Raises
    ------
    FileNotFoundError
        If the local db file is not found.
    """

    if not os.path.exists(local_db):
        raise FileNotFoundError(f"Local cache file {local_db} not found.")

    return json.load(open(local_db, "r"))


@cache
def _local_search_param(name: str) -> list[dict[str, str | int | list[str]]]:
    """Search for a GRIB parameter by name in the local cache.

    This is used to avoid making API calls when the local cache is available.

    Parameters
    ----------
    name : str
        Parameter name to search for.

    Returns
    -------
    list
        A list of dictionaries containing parameter details.

    Raises
    ------
    KeyError
        If no parameter is found.
    """
    local_cache = SETTINGS.paramdb.local_cache
    assert local_cache is not None, "Local cache is not configured."

    local_param_db = _get_local_db(local_cache)

    matched_params = [param for param in local_param_db if param["shortname"] == name]
    if matched_params:
        return matched_params

    raise KeyError(f"{name} not found in local cache.")


@cached(collection="grib", expires=SETTINGS.paramdb.cache_length * 24 * 3600)
def _online_search_param(name: str, **filters) -> list[dict[str, str | int | list[str]]]:
    """Search for a GRIB parameter by name using the online API.

    Parameters
    ----------
    name : str
        Parameter name to search for.
    filters : Any
        Additional filters to disambiguate parameters with the same shortname (e.g. origin, encoding, table, discipline, category).

    Returns
    -------
    list
        A list of dictionaries containing parameter details.
    """
    r = requests.get(
        f"https://codes.ecmwf.int/parameter-database/api/v1/param/?search=^{name}$&regex=true{''.join(f'&{k}={v}' for k, v in filters.items())}"
    )
    r.raise_for_status()
    return r.json()


def _search_param(name: str, **filters) -> dict[str, str | int | list[str]]:
    """Search for a GRIB parameter by name.

    Parameters
    ----------
    name : str
        Parameter name to search for.
    filters : Any
        Additional filters to disambiguate parameters with the same shortname (e.g. origin, encoding, table, discipline, category).

    Returns
    -------
    dict
        A dictionary containing parameter details.

    Raises
    ------
    KeyError
        If no parameter is found.
    """
    if "origin" in filters and isinstance(filters["origin"], str):
        filters["origin"] = origin(filters["origin"])["id"]

    name = re.escape(name)

    if SETTINGS.paramdb.local_cache is not None:
        if filters:
            warnings.warn("Filters are ignored when using local cache.")
        results = _local_search_param(name)
    else:
        results = _online_search_param(name, **filters)

    if len(results) == 0:
        raise KeyError(f"{name} not found in parameter database.")

    if len(results) > 1:
        names = [f"{r.get('id')} ({r.get('name')})" for r in results]
        dissemination = [r for r in results if "dissemination" in r.get("access_ids", [])]  # type: ignore[reportOperatorIssue]
        if len(dissemination) == 1:
            return dissemination[0]

        warnings.warn(f"{name} is ambiguous: {', '.join(names)}.")
        if "origin" not in filters and SETTINGS.paramdb.local_cache is None:
            warnings.warn(f"Applying origin='{SETTINGS.paramdb.default_origin}' in an attempt to disambiguate {name}.")
            try:
                filtered_param = _search_param(name, **{**filters, "origin": SETTINGS.paramdb.default_origin})
                warnings.warn(
                    f"Disambiguated {name} to id: {filtered_param['id']} ({filtered_param.get('name', 'unknown')})."
                )
                return filtered_param
            except KeyError:
                pass

        warnings.warn(f"Failed to disambiguate {name}'. Returning the first match: {names[0]}.")
        results = sorted(results, key=lambda x: x["id"])

    return results[0]


@cached(collection="grib", expires=SETTINGS.paramdb.cache_length * 24 * 3600)
def origin(name: str) -> dict[str, str | int]:
    """Search for an id of an origin by name.

    Parameters
    ----------
    name : str
        Origin name to search for.

    Returns
    -------
    dict
        A dictionary containing origin details.

    Raises
    ------
    KeyError
        If no origin is found.
    """
    name = re.escape(name)
    r = requests.get("https://codes.ecmwf.int/parameter-database/api/v1/origin/")
    r.raise_for_status()
    results = r.json()

    for result in results:
        if result["abbreviation"] == name:
            return result

    raise KeyError(f"{name} not found in origin database.")


def shortname_to_paramid(shortname: str, **filters) -> int:
    """Return the GRIB parameter id given its shortname.

    Parameters
    ----------
    shortname : str
        Parameter shortname.
    filters : Any
        Additional filters to disambiguate parameters with the same shortname (e.g. origin, encoding, table, discipline, category).

    Returns
    -------
    int
        Parameter id.

    >>> shortname_to_paramid("2t")
    167
    """
    return _search_param(shortname, **filters)["id"]  # type: ignore[reportReturnType]


def paramid_to_shortname(paramid: int, **filters) -> str:
    """Return the shortname of a GRIB parameter given its id.

    Parameters
    ----------
    paramid : int
        Parameter id.
    filters : Any
        Additional filters to disambiguate parameters with the same shortname (e.g. origin, encoding, table, discipline, category).

    Returns
    -------
    str
        Parameter shortname.

    >>> paramid_to_shortname(167)
    '2t'
    """
    return _search_param(str(paramid), **filters)["shortname"]  # type: ignore[reportReturnType]


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

    >>> unit(167)
    'K'
    """

    unit_id = str(_search_param(str(param))["unit_id"])
    return _units()[unit_id]


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
