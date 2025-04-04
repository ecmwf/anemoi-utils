# (C) Copyright 2025 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Utilities for working with grids."""

import logging
import os
from io import BytesIO
from typing import List
from typing import Tuple
from typing import Union

import numpy as np
import requests

from .caching import cached

LOG = logging.getLogger(__name__)


GRIDS_URL_PATTERN = "https://get.ecmwf.int/repository/anemoi/grids/grid-{name}.npz"


def xyz_to_latlon(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert Cartesian coordinates to latitude and longitude.

    Parameters
    ----------
    x : np.ndarray
        The x coordinates
    y : np.ndarray
        The y coordinates
    z : np.ndarray
        The z coordinates

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        The latitude and longitude
    """
    return (
        np.rad2deg(np.arcsin(np.minimum(1.0, np.maximum(-1.0, z)))),
        np.rad2deg(np.arctan2(y, x)),
    )


def latlon_to_xyz(lat: np.ndarray, lon: np.ndarray, radius: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert latitude and longitude to Cartesian coordinates.

    Parameters
    ----------
    lat : np.ndarray
        The latitudes
    lon : np.ndarray
        The longitudes
    radius : float, optional
        The radius of the sphere, by default 1.0

    Returns
    -------
    tuple[np.ndarray, np.ndarray, np.ndarray]
        The x, y, and z coordinates
    """
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


def nearest_grid_points(
    source_latitudes: np.ndarray,
    source_longitudes: np.ndarray,
    target_latitudes: np.ndarray,
    target_longitudes: np.ndarray,
) -> np.ndarray:
    """Find the nearest grid points.

    Parameters
    ----------
    source_latitudes : np.ndarray
        The source latitudes
    source_longitudes : np.ndarray
        The source longitudes
    target_latitudes : np.ndarray
        The target latitudes
    target_longitudes : np.ndarray
        The target longitudes

    Returns
    -------
    np.ndarray
        The indices of the nearest grid points
    """
    from scipy.spatial import cKDTree

    source_xyz = latlon_to_xyz(source_latitudes, source_longitudes)
    source_points = np.array(source_xyz).transpose()

    target_xyz = latlon_to_xyz(target_latitudes, target_longitudes)
    target_points = np.array(target_xyz).transpose()

    _, indices = cKDTree(source_points).query(target_points, k=1)
    return indices


@cached(collection="grids", encoding="npz")
def _grids(name: Union[str, List[float], Tuple[float, ...]]) -> bytes:
    """Get grid data by name.

    Parameters
    ----------
    name : str
        The name of the grid

    Returns
    -------
    bytes
        The grid data
    """
    from anemoi.utils.config import load_config

    if isinstance(name, (tuple, list)):
        assert len(name) == 2, "Grid name must be a list or a tuple of length 2"
        assert all(isinstance(i, (int, float)) for i in name), "Grid name must be a list or a tuple of numbers"
        if name[0] == name[1]:
            name = str(float(name[0]))
        else:
            name = str(float(name[0])) + "x" + str(float(name[1]))
        name = name.replace(".", "p")

    user_path = load_config().get("utils", {}).get("grids_path")
    if user_path:
        path = os.path.expanduser(os.path.join(user_path, f"grid-{name}.npz"))
        if os.path.exists(path):
            LOG.warning("Loading grids from custom user path %s", path)
            with open(path, "rb") as f:
                return f.read()
        else:
            LOG.warning("Custom user path %s does not exist", path)

    # To add a grid
    # anemoi-transform get-grid --source mars grid=o400,levtype=sfc,param=2t grid-o400.npz
    # nexus-cli -u xxxx -p yyyy -s GET_INSTANCE --repository anemoi upload --remote-path grids --local-path grid-o400.npz

    url = GRIDS_URL_PATTERN.format(name=name.lower())
    LOG.warning("Downloading grids from %s", url)
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def grids(name: Union[str, List[float], Tuple[float, ...]]) -> dict:
    """Load grid data by name.

    Parameters
    ----------
    name : str
        The name of the grid

    Returns
    -------
    dict
        The grid data
    """
    if isinstance(name, str) and name.endswith(".npz"):
        return dict(np.load(name))

    data = _grids(name)
    npz = np.load(BytesIO(data))
    return dict(npz)
