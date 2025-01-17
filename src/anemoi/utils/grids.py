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
import os
from io import BytesIO

import numpy as np
import requests

from .caching import cached

LOG = logging.getLogger(__name__)


GRIDS_URL_PATTERN = "https://get.ecmwf.int/repository/anemoi/grids/grid-{name}.npz"


def xyz_to_latlon(x, y, z):
    return (
        np.rad2deg(np.arcsin(np.minimum(1.0, np.maximum(-1.0, z)))),
        np.rad2deg(np.arctan2(y, x)),
    )


def latlon_to_xyz(lat, lon, radius=1.0):
    # https://en.wikipedia.org/wiki/Geographic_coordinate_conversion#From_geodetic_to_ECEF_coordinates
    # We assume that the Earth is a sphere of radius 1 so N(phi) = 1
    # We assume h = 0
    #
    phi = np.deg2rad(lat)
    lda = np.deg2rad(lon)

    cos_phi = np.cos(phi)
    cos_lda = np.cos(lda)
    sin_phi = np.sin(phi)
    sin_lda = np.sin(lda)

    x = cos_phi * cos_lda * radius
    y = cos_phi * sin_lda * radius
    z = sin_phi * radius

    return x, y, z


def nearest_grid_points(source_latitudes, source_longitudes, target_latitudes, target_longitudes):
    from scipy.spatial import cKDTree

    source_xyz = latlon_to_xyz(source_latitudes, source_longitudes)
    source_points = np.array(source_xyz).transpose()

    target_xyz = latlon_to_xyz(target_latitudes, target_longitudes)
    target_points = np.array(target_xyz).transpose()

    _, indices = cKDTree(source_points).query(target_points, k=1)
    return indices


@cached(collection="grids", encoding="npz")
def _grids(name):
    from anemoi.utils.config import load_config

    user_path = load_config().get("utils", {}).get("grids_path")
    if user_path:
        path = os.path.expanduser(os.path.join(user_path, f"grid-{name}.npz"))
        if os.path.exists(path):
            LOG.warning("Loading grids from custom user path %s", path)
            with open(path, "rb") as f:
                return f.read()
        else:
            LOG.warning("Custom user path %s does not exist", path)

    url = GRIDS_URL_PATTERN.format(name=name.lower())
    LOG.warning("Downloading grids from %s", url)
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def grids(name):
    if name.endswith(".npz"):
        return dict(np.load(name))

    data = _grids(name)
    npz = np.load(BytesIO(data))
    return dict(npz)
