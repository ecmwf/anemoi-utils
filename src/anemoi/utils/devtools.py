# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import matplotlib.tri as tri
import numpy as np

"""FOR DEVELOPMENT PURPOSES ONLY

This module contains

"""

# TODO: use earthkit-plots


def fix(lons):
    return np.where(lons > 180, lons - 360, lons)


def plot_values(
    values, latitudes, longitudes, title=None, missing_value=None, min_value=None, max_value=None, **kwargs
):

    _, ax = plt.subplots(subplot_kw={"projection": ccrs.PlateCarree()})
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=":")

    missing_values = np.isnan(values)

    if missing_value is None:
        values = values[~missing_values]
        longitudes = longitudes[~missing_values]
        latitudes = latitudes[~missing_values]
    else:
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


def plot_field(field, title=None, **kwargs):
    values = field.to_numpy(flatten=True)
    latitudes, longitudes = field.grid_points()
    return plot_values(values, latitudes, longitudes, title=title, **kwargs)
