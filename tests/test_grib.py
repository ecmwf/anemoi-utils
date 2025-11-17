# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from anemoi.utils.grib import paramid_to_shortname
from anemoi.utils.grib import shortname_to_paramid


def test_grib() -> None:
    """Test the GRIB utility functions.

    Tests:
        - Converting short names to parameter IDs.
        - Converting parameter IDs to short names.
    """
    assert shortname_to_paramid("2t") == 167
    assert paramid_to_shortname(167) == "2t"


if __name__ == "__main__":
    """Run all test functions."""
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
