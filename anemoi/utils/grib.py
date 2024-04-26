# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import re

import requests


def _search(name):
    name = re.escape(name)
    r = requests.get(f"https://codes.ecmwf.int/parameter-database/api/v1/param/?search=^{name}$&regex=true")
    r.raise_for_status()
    results = r.json()
    if len(results) == 0:
        raise KeyError(name)

    if len(results) > 1:
        names = [f'{r.get("id")} ({r.get("name")})' for r in results]
        raise ValueError(f"{name} is ambiguous: {', '.join(names)}")

    return results[0]


def shortname_to_paramid(shortname: str) -> int:
    """Return the GRIB parameter id given its shortname.

    Parameters
    ----------
    shortname : str
        Parameter shortname.

    Returns
    -------
    int
        Parameter id.
    """
    return _search(shortname)["id"]


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
    """
    return _search(str(paramid))["shortname"]
