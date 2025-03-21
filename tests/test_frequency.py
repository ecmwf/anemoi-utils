# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import datetime

from anemoi.utils.dates import frequency_to_string
from anemoi.utils.dates import frequency_to_timedelta


def test_frequency_to_string() -> None:
    """Test the frequency_to_string function for converting timedelta to string."""
    assert frequency_to_string(datetime.timedelta(hours=1)) == "1h"
    assert frequency_to_string(datetime.timedelta(hours=1, minutes=30)) == "1:30:00"
    assert frequency_to_string(datetime.timedelta(days=10)) == "10d"
    assert frequency_to_string(datetime.timedelta(minutes=10)) == "10m"
    assert frequency_to_string(datetime.timedelta(minutes=90)) == "1:30:00"


def test_frequency_to_timedelta() -> None:
    """Test the frequency_to_timedelta function for converting string to timedelta."""
    assert frequency_to_timedelta("1s") == datetime.timedelta(seconds=1)
    assert frequency_to_timedelta("3m") == datetime.timedelta(minutes=3)
    assert frequency_to_timedelta("1h") == datetime.timedelta(hours=1)
    assert frequency_to_timedelta("3d") == datetime.timedelta(days=3)
    assert frequency_to_timedelta("90m") == datetime.timedelta(hours=1, minutes=30)
    assert frequency_to_timedelta("0:30") == datetime.timedelta(minutes=30)
    assert frequency_to_timedelta("0:30:10") == datetime.timedelta(minutes=30, seconds=10)
    assert frequency_to_timedelta("1:30:10") == datetime.timedelta(hours=1, minutes=30, seconds=10)

    assert frequency_to_timedelta("PT10M") == datetime.timedelta(minutes=10)


if __name__ == "__main__":
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
