# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import datetime
from typing import Iterator
from typing import List
from typing import Tuple


class HindcastDatesTimes:
    """The HindcastDatesTimes class is an iterator that generates datetime objects within a given range.

    Attributes
    ----------
    reference_dates : List[datetime.datetime]
        List of reference dates.
    years : int
        Number of years to go back from each reference date.
    """

    def __init__(self, reference_dates: List[datetime.datetime], years: int = 20):
        """Initialize the HindcastDatesTimes iterator.

        Parameters
        ----------
        reference_dates : List[datetime.datetime]
            List of reference dates.
        years : int, optional
            Number of years to go back from each reference date, by default 20.
        """
        self.reference_dates = reference_dates

        assert isinstance(years, int), f"years must be an integer, got {years}"
        assert years > 0, f"years must be greater than 0, got {years}"
        self.years = years

    def __iter__(self) -> Iterator[Tuple[datetime.datetime, datetime.datetime]]:
        """Generate tuples of past dates and their corresponding reference dates.

        Yields
        ------
        Iterator[Tuple[datetime.datetime, datetime.datetime]]
            Tuples containing a past date and its corresponding reference date.
        """
        for reference_date in self.reference_dates:
            year, month, day = reference_date.year, reference_date.month, reference_date.day
            if (month, day) == (2, 29):
                day = 28

            for i in range(1, self.years + 1):
                date = datetime.datetime(year - i, month, day)
                yield (date, reference_date)
