# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import datetime
from textwrap import dedent

import yaml

from anemoi.utils.dates import datetimes_factory


def _(txt: str) -> datetimes_factory:
    """Helper function to create a datetimes_factory from a YAML string.

    Parameters
    ----------
    txt : str
        The YAML string.

    Returns
    -------
    datetimes_factory
        The datetimes_factory object.
    """
    txt = dedent(txt)
    config = yaml.safe_load(txt)
    return datetimes_factory(config)


def test_date_1() -> None:
    """Test datetimes_factory with a list of dates."""
    d = _(
        """
          - 2023-01-01
          - 2023-01-02
          - 2023-01-03
    """
    )
    assert len(list(d)) == 3


def test_date_2() -> None:
    """Test datetimes_factory with a date range and frequency."""
    d = _(
        """
        start: 2023-01-01
        end: 2023-01-07
        frequency: 12
        day_of_week: [monday, friday]
    """
    )
    assert len(list(d)) == 4


def test_date_3() -> None:
    """Test datetimes_factory with multiple date ranges and frequencies."""
    d = _(
        """
        - start: 2023-01-01
          end: 2023-01-03
          frequency: 24
        - start: 2024-01-01T06:00:00
          end: 2024-01-02T18:00:00
          frequency: 6h
    """
    )
    assert datetime.datetime(2023, 1, 1, 0) in d
    assert datetime.datetime(2023, 1, 2, 0) in d
    assert datetime.datetime(2023, 1, 3, 0) in d
    assert datetime.datetime(2024, 1, 1, 6) in d
    assert datetime.datetime(2024, 1, 1, 12) in d
    assert datetime.datetime(2024, 1, 1, 18) in d
    assert datetime.datetime(2024, 1, 2, 0) in d
    assert datetime.datetime(2024, 1, 2, 6) in d
    assert datetime.datetime(2024, 1, 2, 12) in d
    assert datetime.datetime(2024, 1, 2, 18) in d
    assert len(list(d)) == 10


def test_date_hindcast_1() -> None:
    """Test datetimes_factory with hindcast configuration."""
    d = _(
        """
        - name: hindcast
          reference_dates:
            start: 2023-01-01
            end: 2023-01-03
            frequency: 24
          years: 20
    """
    )
    assert len(list(d)) == 60


if __name__ == "__main__":
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
