# (C) Copyright 2025 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Utilities for working with grids.

"""

import logging
from io import BytesIO

import numpy as np
import requests

from .caching import cached

LOG = logging.getLogger(__name__)


GRIDS_URL_PATTERN = "https://get.ecmwf.int/repository/anemoi/grids/grid-{name}.npz"


@cached(collection="grids", encoding="npz")
def _grids(name):
    url = GRIDS_URL_PATTERN.format(name=name.lower())
    LOG.error("Downloading grids from %s", url)
    LOG.warning("Downloading grids from %s", url)
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def grids(name):
    data = _grids(name)
    npz = np.load(BytesIO(data))
    return dict(npz)
