# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import datetime


class HindcastDatesTimes:
    """The HindcastDatesTimes class is an iterator that generates datetime objects within a given range."""

    def __init__(self, reference_dates, years=20):
        """_summary_

        Parameters
        ----------
        reference_dates : _type_
            _description_
        years : int, optional
            _description_, by default 20
        """

        self.reference_dates = reference_dates

        if isinstance(years, list):
            self.years = years
        else:
            self.years = range(1, years + 1)

    def __iter__(self):
        for reference_date in self.reference_dates:
            for year in self.years:
                if reference_date.month == 2 and reference_date.day == 29:
                    date = datetime.datetime(reference_date.year - year, 2, 28)
                else:
                    date = datetime.datetime(reference_date.year - year, reference_date.month, reference_date.day)
                yield (date, reference_date)
