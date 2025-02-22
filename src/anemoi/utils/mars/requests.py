# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import sys
from typing import Any
from typing import Dict
from typing import TextIO


def print_request(verb: str, request: Dict[str, Any], file: TextIO = sys.stdout) -> None:
    """Prints a formatted request.

    Parameters
    ----------
    verb : str
        A mars verb
    request : Dict[str, Any]
        The request parameters.
    file : TextIO, optional
        The file to which the request is printed, by default sys.stdout.
    """
    r = [verb]
    for k, v in request.items():
        if not isinstance(v, (list, tuple, set)):
            v = [v]
        v = [str(_) for _ in v]
        v = "/".join(v)
        r.append(f"{k}={v}")

    r = ",\n   ".join(r)
    print(r, file=file)
    print(file=file)
