# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import calendar
import datetime

from .hindcasts import HindcastDatesTimes


def normalise_frequency(frequency):
    if isinstance(frequency, int):
        return frequency
    assert isinstance(frequency, str), (type(frequency), frequency)

    unit = frequency[-1].lower()
    v = int(frequency[:-1])
    return {"h": v, "d": v * 24}[unit]


def no_time_zone(date):
    """Remove time zone information from a date.

    Parameters
    ----------
    date : datetime.datetime
        A datetime object.

    Returns
    -------
    datetime.datetime
        The datetime object without time zone information.
    """

    return date.replace(tzinfo=None)


# this function is use in anemoi-datasets
def as_datetime(date):
    """Convert a date to a datetime object, removing any time zone information.

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
        return no_time_zone(date)

    if isinstance(date, datetime.date):
        return no_time_zone(datetime.datetime(date.year, date.month, date.day))

    if isinstance(date, str):
        return no_time_zone(datetime.datetime.fromisoformat(date))

    raise ValueError(f"Invalid date type: {type(date)}")


DOW = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


MONTH = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _make_day(day):
    if day is None:
        return set(range(1, 32))
    if not isinstance(day, list):
        day = [day]
    return {int(d) for d in day}


def _make_week(week):
    if week is None:
        return set(range(7))
    if not isinstance(week, list):
        week = [week]
    return {DOW[w.lower()] for w in week}


def _make_months(months):
    if months is None:
        return set(range(1, 13))

    if not isinstance(months, list):
        months = [months]

    return {int(MONTH.get(m, m)) for m in months}


class DateTimes:
    """The DateTimes class is an iterator that generates datetime objects within a given range."""

    def __init__(self, start, end, increment=24, *, day_of_month=None, day_of_week=None, calendar_months=None):
        """_summary_

        Parameters
        ----------
        start : _type_
            _description_
        end : _type_
            _description_
        increment : int, optional
            _description_, by default 24
        day_of_month : _type_, optional
            _description_, by default None
        day_of_week : _type_, optional
            _description_, by default None
        calendar_months : _type_, optional
            _description_, by default None
        """
        self.start = as_datetime(start)
        self.end = as_datetime(end)
        self.increment = datetime.timedelta(hours=increment)
        self.day_of_month = _make_day(day_of_month)
        self.day_of_week = _make_week(day_of_week)
        self.calendar_months = _make_months(calendar_months)

    def __iter__(self):
        date = self.start
        while date <= self.end:
            if (
                (date.weekday() in self.day_of_week)
                and (date.day in self.day_of_month)
                and (date.month in self.calendar_months)
            ):

                yield date
            date += self.increment


class Year(DateTimes):
    """Year is defined as the months of January to December."""

    def __init__(self, year, **kwargs):
        """_summary_

        Parameters
        ----------
        year : int
            _description_
        """
        super().__init__(datetime.datetime(year, 1, 1), datetime.datetime(year, 12, 31), **kwargs)


class Winter(DateTimes):
    """Winter is defined as the months of December, January and February."""

    def __init__(self, year, **kwargs):
        """_summary_

        Parameters
        ----------
        year : int
            _description_
        """
        super().__init__(
            datetime.datetime(year, 12, 1),
            datetime.datetime(year + 1, 2, calendar.monthrange(year + 1, 2)[1]),
            **kwargs,
        )


class Spring(DateTimes):
    """Spring is defined as the months of March, April and May."""

    def __init__(self, year, **kwargs):
        """_summary_

        Parameters
        ----------
        year : int
            _description_
        """
        super().__init__(datetime.datetime(year, 3, 1), datetime.datetime(year, 5, 31), **kwargs)


class Summer(DateTimes):
    """Summer is defined as the months of June, July and August."""

    def __init__(self, year, **kwargs):
        """_summary_

        Parameters
        ----------
        year : int
            _description_
        """
        super().__init__(datetime.datetime(year, 6, 1), datetime.datetime(year, 8, 31), **kwargs)


class Autumn(DateTimes):
    """Autumn is defined as the months of September, October and November."""

    def __init__(self, year, **kwargs):
        """_summary_

        Parameters
        ----------
        year : int
            _description_
        """
        super().__init__(datetime.datetime(year, 9, 1), datetime.datetime(year, 11, 30), **kwargs)


class ConcatDateTimes:
    def __init__(self, *dates):
        if len(dates) == 1 and isinstance(dates[0], list):
            dates = dates[0]

        self.dates = dates

    def __iter__(self):
        for date in self.dates:
            yield from date


class EnumDateTimes:
    def __init__(self, dates):
        self.dates = dates

    def __iter__(self):
        for date in self.dates:
            yield as_datetime(date)


def datetimes_factory(*args, **kwargs):
    if args and kwargs:
        raise ValueError("Cannot provide both args and kwargs for a list of dates")

    if not args and not kwargs:
        raise ValueError("No dates provided")

    if kwargs:
        name = kwargs.get("name")

        if name == "hindcast":
            reference_dates = kwargs["reference_dates"]
            reference_dates = datetimes_factory(reference_dates)
            years = kwargs["years"]
            return HindcastDatesTimes(reference_dates=reference_dates, years=years)

        kwargs = kwargs.copy()
        if "frequency" in kwargs:
            freq = kwargs.pop("frequency")
            kwargs["increment"] = normalise_frequency(freq)
        return DateTimes(**kwargs)

    if not any((isinstance(x, dict) or isinstance(x, list)) for x in args):
        return EnumDateTimes(args)

    if len(args) == 1:
        a = args[0]

        if isinstance(a, dict):
            return datetimes_factory(**a)

        if isinstance(a, list):
            return datetimes_factory(*a)

    return ConcatDateTimes(*[datetimes_factory(a) for a in args])
