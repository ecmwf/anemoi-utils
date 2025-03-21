# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from typing import Any

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import matplotlib.tri as tri
import numpy as np

"""FOR DEVELOPMENT PURPOSES ONLY.

This module contains
"""

# TODO: use earthkit-plots


def fix(lons: np.ndarray) -> np.ndarray:
    """Fix longitudes greater than 180 degrees.

    Parameters
    ----------
    lons : np.ndarray
        Array of longitudes.

    Returns
    -------
    np.ndarray
        Array of fixed longitudes.
    """
    return np.where(lons > 180, lons - 360, lons)


def plot_values(
    values: np.ndarray,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    title: str = None,
    missing_value: float = None,
    min_value: float = None,
    max_value: float = None,
    **kwargs: dict,
) -> plt.Axes:
    """Plot values on a map.

    Parameters
    ----------
    values : np.ndarray
        Array of values to plot.
    latitudes : np.ndarray
        Array of latitudes.
    longitudes : np.ndarray
        Array of longitudes.
    title : str, optional
        Title of the plot, by default None.
    missing_value : float, optional
        Value to use for missing data, by default None.
    min_value : float, optional
        Minimum value for the plot, by default None.
    max_value : float, optional
        Maximum value for the plot, by default None.
    **kwargs : dict
        Additional keyword arguments for the plot.

    Returns
    -------
    plt.Axes
        The plot axes.
    """
    _, ax = plt.subplots(subplot_kw={"projection": ccrs.PlateCarree()})
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=":")

    missing_values = np.isnan(values)
    if missing_value is None:
        min = np.nanmin(values)
        missing_value = min - np.abs(min) * 0.001

    values = np.where(missing_values, missing_value, values)

    if max_value is not None:
        values = np.where(values > max_value, max_value, values)

    if min_value is not None:
        values = np.where(values < min_value, min_value, values)

    triangulation = tri.Triangulation(fix(longitudes), latitudes)

    levels = kwargs.pop("levels", 10)

    _ = ax.tricontourf(triangulation, values, levels=levels, transform=ccrs.PlateCarree())

    options = dict(
        levels=levels,
        colors="black",
        linewidths=0.5,
        transform=ccrs.PlateCarree(),
    )

    options.update(kwargs)

    ax.tricontour(
        triangulation,
        values,
        **options,
    )

    if title is not None:
        ax.set_title(title)

    return ax


def plot_field(field: Any, title: str = None, **kwargs: dict) -> plt.Axes:
    """Plot a field on a map.

    Parameters
    ----------
    field : Any
        The field to plot.
    title : str, optional
        Title of the plot, by default None.
    **kwargs : dict
        Additional keyword arguments for the plot.

    Returns
    -------
    plt.Axes
        The plot axes.
    """
    values = field.to_numpy(flatten=True)
    latitudes, longitudes = field.grid_points()
    return plot_values(values, latitudes, longitudes, title=title, **kwargs)
