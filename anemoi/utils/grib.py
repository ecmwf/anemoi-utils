# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import re

import requests


def shortname_to_paramid(name):
    name = re.escape(name)
    r = requests.get(f"https://codes.ecmwf.int/parameter-database/api/v1/param/?search=^{name}$&regex=true")
    r.raise_for_status()
    results = r.json()
    if len(results) == 0:
        raise KeyError(name)

    if len(results) > 1:
        raise ValueError(f"{name} is ambiguous")

    return results[0]["id"]
