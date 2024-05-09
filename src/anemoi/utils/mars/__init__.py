# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Utilities for working with Mars requests.

Has some konwledge of how certain streams are organised in Mars.

"""

import datetime
import logging
import os

import yaml

LOG = logging.getLogger(__name__)

DEFAULT_MARS_LABELLING = {
    "class": "od",
    "type": "an",
    "stream": "oper",
    "expver": "0001",
}


def _expand_mars_labelling(request):
    """Expand the request with the default Mars labelling.

    The default Mars labelling is:

    {'class': 'od',
     'type': 'an',
     'stream': 'oper',
     'expver': '0001'}

    """
    result = DEFAULT_MARS_LABELLING.copy()
    result.update(request)
    return result


STREAMS = None


def _lookup_mars_stream(request):
    global STREAMS

    if STREAMS is None:

        with open(os.path.join(os.path.dirname(__file__), "mars.yaml")) as f:
            STREAMS = yaml.safe_load(f)

    request = _expand_mars_labelling(request)
    for s in STREAMS:
        match = s["match"]
        if all(request.get(k) == v for k, v in match.items()):
            return s["info"]


def recenter(date, center, members):

    center = _lookup_mars_stream(center)
    members = _lookup_mars_stream(members)

    return (center, members)


if __name__ == "__main__":
    date = datetime.datetime(2024, 5, 9, 0)

    print(recenter(date, {"type": "an"}, {"stream": "elda"}))
