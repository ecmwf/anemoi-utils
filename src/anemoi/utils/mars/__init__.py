# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Utilities for working with Mars requests.

Has some knowledge of how certain streams are organised in Mars.
"""

import datetime
import logging
import os
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

import yaml

LOG = logging.getLogger(__name__)

DEFAULT_MARS_LABELLING = {
    "class": "od",
    "type": "an",
    "stream": "oper",
    "expver": "0001",
}


def _expand_mars_labelling(request: Dict[str, Any]) -> Dict[str, Any]:
    """Expand the request with the default Mars labelling.

    Parameters
    ----------
    request : dict
        The original Mars request.

    Returns
    -------
    dict
        The Mars request expanded with default labelling.
    """
    result = DEFAULT_MARS_LABELLING.copy()
    result.update(request)
    return result


STREAMS = None


def _lookup_mars_stream(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Look up the Mars stream information for a given request.

    Parameters
    ----------
    request : dict
        The Mars request.

    Returns
    -------
    dict or None
        The stream information if a match is found, otherwise None.
    """
    global STREAMS

    if STREAMS is None:

        with open(os.path.join(os.path.dirname(__file__), "mars.yaml")) as f:
            STREAMS = yaml.safe_load(f)

    request = _expand_mars_labelling(request)
    for s in STREAMS:
        match = s["match"]
        if all(request.get(k) == v for k, v in match.items()):
            return s["info"]


def recenter(
    date: datetime.datetime, center: Dict[str, Any], members: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Recenter the given date with the specified center and members.

    Parameters
    ----------
    date : datetime.datetime
        The date to recenter.
    center : dict
        The center request information.
    members : dict
        The members request information.

    Returns
    -------
    tuple
        A tuple containing the recentered center and members information.
    """
    center = _lookup_mars_stream(center)
    members = _lookup_mars_stream(members)

    return (center, members)


if __name__ == "__main__":
    date = datetime.datetime(2024, 5, 9, 0)

    print(recenter(date, {"type": "an"}, {"stream": "elda"}))
