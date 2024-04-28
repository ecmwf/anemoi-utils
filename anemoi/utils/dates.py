# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import calendar
import datetime


def no_time_zone(date):
    return date.replace(tzinfo=None)


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

    def __init__(self, start, end, increment=24, *, day_of_month=None, day_of_week=None, calendar_months=None):
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


class HindcastDatesTimes:

    def __init__(self, reference_dates, years=20):

        self.reference_dates = reference_dates
        self.years = (1, years + 1)

    def __iter__(self):
        for reference_date in self.reference_dates:
            for year in range(*self.years):
                if reference_date.month == 2 and reference_date.day == 29:
                    date = datetime.datetime(reference_date.year - year, 2, 28)
                else:
                    date = datetime.datetime(reference_date.year - year, reference_date.month, reference_date.day)
                yield (date, reference_date)


class Year(DateTimes):

    def __init__(self, year, **kwargs):
        super().__init__(datetime.datetime(year, 1, 1), datetime.datetime(year, 12, 31), **kwargs)


class Winter(DateTimes):

    def __init__(self, year, **kwargs):
        super().__init__(
            datetime.datetime(year, 12, 1),
            datetime.datetime(year + 1, 2, calendar.monthrange(year + 1, 2)[1]),
            **kwargs,
        )


class Spring(DateTimes):

    def __init__(self, year, **kwargs):
        super().__init__(datetime.datetime(year, 3, 1), datetime.datetime(year, 5, 31), **kwargs)


class Summer(DateTimes):

    def __init__(self, year, **kwargs):
        super().__init__(datetime.datetime(year, 6, 1), datetime.datetime(year, 8, 31), **kwargs)


class Autumn(DateTimes):

    def __init__(self, year, **kwargs):
        super().__init__(datetime.datetime(year, 9, 1), datetime.datetime(year, 11, 30), **kwargs)
