# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import datetime


def as_datetime(date):
    """Convert a date to a datetime object.

    Parameters
    ----------
    date : datetime.date or datetime.datetime or str
        The date to convert.

    Returns
    -------
    datetime.datetime
        The datetime object.
    """
    if isinstance(date, datetime.datetime):
        return date
    if isinstance(date, datetime.date):
        return datetime.datetime(date.year, date.month, date.day)
    if isinstance(date, str):
        return datetime.datetime.strptime(date, "%Y-%m-%d")
    raise ValueError(f"Invalid date type: {type(date)}")
