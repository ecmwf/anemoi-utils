# (C) Copyright 2025 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from anemoi.utils.grids import grids


def test_o96() -> None:
    """Test the grids function for the 'o96' grid."""
    x = grids("o96")
    assert x["latitudes"].mean() == 0.0
    assert x["longitudes"].mean() == 179.14285714285714
    assert x["latitudes"].shape == (40320,)
    assert x["longitudes"].shape == (40320,)
    assert x["latitudes"][31415] == -31.324557701757268
    assert x["longitudes"][31415] == 224.32835820895522


if __name__ == "__main__":
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
