# (C) Copyright 2024 Anemoi contributors.
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

import logging
import re

import requests

from .caching import cached
from .config import load_config

LOG = logging.getLogger(__name__)
CONFIG = load_config().get("param_db", {})

cache_length = CONFIG.get("cache_length", 30) * 24 * 60 * 60
default_origin = CONFIG.get("default_origin", "ecmf")


@cached(collection="grib", expires=cache_length)
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


@cached(collection="grib", expires=cache_length)
def _search_param(name: str, **filters) -> dict[str, str | int]:
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
        filters["origin"] = _search_origin(filters["origin"])["id"]

    name = re.escape(name)
    r = requests.get(
        f"https://codes.ecmwf.int/parameter-database/api/v1/param/?search=^{name}$&regex=true{ ''.join(f'&{k}={v}' for k, v in filters.items()) }"
    )
    r.raise_for_status()
    results = r.json()
    if len(results) == 0:
        raise KeyError(name)

    if len(results) > 1:
        names = [f'{r.get("id")} ({r.get("name")})' for r in results]
        dissemination = [r for r in results if "dissemination" in r.get("access_ids", [])]
        if len(dissemination) == 1:
            return dissemination[0]

        LOG.warning(
            f"{name} is ambiguous: {', '.join(names)}. Try filtering with 'origin','encoding','table','discipline' or 'category' to disambiguate."
        )
        if "origin" not in filters:
            LOG.warning(f"Applying origin='{default_origin}' to disambiguate {name}.")
            try:
                return _search_param(name, **{**filters, "origin": default_origin})
            except KeyError:
                LOG.warning(
                    f"Failed to disambiguate {name} with origin='{default_origin}'. Returning the first match: {names[0]}."
                )

        results = sorted(results, key=lambda x: x["id"])

    return results[0]


@cached(collection="grib", expires=30 * 24 * 60 * 60)
def _search_origin(name: str) -> dict[str, str | int]:
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

    raise KeyError(name)


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
    return _search_param(shortname, **filters)["id"]


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
    return _search_param(str(paramid), **filters)["shortname"]


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
