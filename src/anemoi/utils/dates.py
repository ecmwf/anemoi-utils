# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import calendar
import datetime
import re
from typing import Any
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Union

import aniso8601


def normalise_frequency(frequency: Union[int, str]) -> int:
    """Normalise frequency to hours.

    Parameters
    ----------
    frequency : int or str
        The frequency to normalise.

    Returns
    -------
    int
        The normalised frequency in hours.
    """
    if isinstance(frequency, int):
        return frequency
    assert isinstance(frequency, str), (type(frequency), frequency)

    unit = frequency[-1].lower()
    v = int(frequency[:-1])
    return {"h": v, "d": v * 24}[unit]


def _no_time_zone(date: datetime.datetime) -> datetime.datetime:
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
def as_datetime(date: Union[datetime.date, datetime.datetime, str], keep_time_zone: bool = False) -> datetime.datetime:
    """Convert a date to a datetime object, removing any time zone information.

    Parameters
    ----------
    date : datetime.date or datetime.datetime or str
        The date to convert.
    keep_time_zone : bool, optional
        If True, the time zone information is kept, by default False.

    Returns
    -------
    datetime.datetime
        The datetime object.
    """

    tidy = _no_time_zone if not keep_time_zone else lambda x: x

    if isinstance(date, datetime.datetime):
        return tidy(date)

    if isinstance(date, datetime.date):
        return tidy(datetime.datetime(date.year, date.month, date.day))

    if isinstance(date, str):
        return tidy(datetime.datetime.fromisoformat(date))

    raise ValueError(f"Invalid date type: {type(date)}")


def _as_datetime_list(
    date: Union[datetime.date, datetime.datetime, str], default_increment: datetime.timedelta
) -> iter:
    """Convert a date to a list of datetime objects.

    Parameters
    ----------
    date : datetime.date or datetime.datetime or str
        The date to convert.
    default_increment : datetime.timedelta
        The default increment for the list.

    Returns
    -------
    iter
        An iterator of datetime objects.
    """
    if isinstance(date, (list, tuple)):
        for d in date:
            yield from _as_datetime_list(d, default_increment)

    if isinstance(date, str):
        # Check for ISO format
        try:
            start, end = aniso8601.parse_interval(date)
            while start <= end:
                yield as_datetime(start)
                start += default_increment

            return

        except aniso8601.exceptions.ISOFormatError:
            pass

        try:
            intervals = aniso8601.parse_repeating_interval(date)
            for date in intervals:
                yield as_datetime(date)
            return
        except aniso8601.exceptions.ISOFormatError:
            pass

    yield as_datetime(date)


def as_datetime_list(
    date: Union[datetime.date, datetime.datetime, str], default_increment: int = 1
) -> list[datetime.datetime]:
    """Convert a date to a list of datetime objects.

    Parameters
    ----------
    date : datetime.date or datetime.datetime or str
        The date to convert.
    default_increment : int, optional
        The default increment in hours, by default 1.

    Returns
    -------
    list of datetime.datetime
        A list of datetime objects.
    """
    default_increment = frequency_to_timedelta(default_increment)
    return list(_as_datetime_list(date, default_increment))


def as_timedelta(frequency: Union[int, str, datetime.timedelta]) -> datetime.timedelta:
    """Convert anything to a timedelta object.

    Parameters
    ----------
    frequency : int or str or datetime.timedelta
        The frequency to convert. If an integer, it is assumed to be in hours. If a string, it can be in the format:

        - "1h" for 1 hour
        - "1d" for 1 day
        - "1m" for 1 minute
        - "1s" for 1 second
        - "1:30" for 1 hour and 30 minutes
        - "1:30:10" for 1 hour, 30 minutes and 10 seconds
        - "PT10M" for 10 minutes (ISO8601)

        If a timedelta object is provided, it is returned as is.

    Returns
    -------
    datetime.timedelta
        The timedelta object.

    Raises
    ------
    ValueError
        Exception raised if the frequency cannot be converted to a timedelta.
    """

    if isinstance(frequency, datetime.timedelta):
        return frequency

    if isinstance(frequency, int):
        return datetime.timedelta(hours=frequency)

    assert isinstance(frequency, str), (type(frequency), frequency)

    try:
        return frequency_to_timedelta(int(frequency))
    except ValueError:
        pass

    if frequency.startswith(" ") or frequency.startswith(" "):
        frequency = frequency.strip()

    if frequency.startswith("-"):
        return -as_timedelta(frequency[1:])

    if frequency.startswith("+"):
        return as_timedelta(frequency[1:])

    if re.match(r"^\d+[hdms]$", frequency, re.IGNORECASE):
        unit = frequency[-1].lower()
        v = int(frequency[:-1])
        unit = {"h": "hours", "d": "days", "s": "seconds", "m": "minutes"}[unit]
        return datetime.timedelta(**{unit: v})

    if re.match(r"^\d+:\d+(:\d+)?$", frequency):
        m = frequency.split(":")
        if len(m) == 2:
            return datetime.timedelta(hours=int(m[0]), minutes=int(m[1]))

        if len(m) == 3:
            return datetime.timedelta(hours=int(m[0]), minutes=int(m[1]), seconds=int(m[2]))

    if re.match(r"^\d+ days?, \d+:\d+:\d+$", frequency):
        m = frequency.split(", ")
        days = int(m[0].split()[0])
        hms = m[1].split(":")
        return datetime.timedelta(days=days, hours=int(hms[0]), minutes=int(hms[1]), seconds=int(hms[2]))

    # ISO8601
    try:
        return aniso8601.parse_duration(frequency)
    except aniso8601.exceptions.ISOFormatError:
        pass

    raise ValueError(f"Cannot convert frequency {frequency} to timedelta")


def frequency_to_timedelta(frequency: Union[int, str, datetime.timedelta]) -> datetime.timedelta:
    """Convert a frequency to a timedelta object.

    Parameters
    ----------
    frequency : int or str or datetime.timedelta
        The frequency to convert.

    Returns
    -------
    datetime.timedelta
        The timedelta object.
    """
    return as_timedelta(frequency)


def frequency_to_string(frequency: datetime.timedelta) -> str:
    """Convert a frequency (i.e. a datetime.timedelta) to a string.

    Parameters
    ----------
    frequency : datetime.timedelta
        The frequency to convert.

    Returns
    -------
    str
        A string representation of the frequency.
    """

    frequency = frequency_to_timedelta(frequency)

    total_seconds = frequency.total_seconds()
    if total_seconds < 0:
        return f"-{frequency_to_string(-frequency)}"
    assert int(total_seconds) == total_seconds, total_seconds
    total_seconds = int(total_seconds)

    seconds = total_seconds

    days = seconds // (24 * 3600)
    seconds %= 24 * 3600
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    if days > 0 and hours == 0 and minutes == 0 and seconds == 0:
        return f"{days}d"

    if days == 0 and hours > 0 and minutes == 0 and seconds == 0:
        return f"{hours}h"

    if days == 0 and hours == 0 and minutes > 0 and seconds == 0:
        return f"{minutes}m"

    if days == 0 and hours == 0 and minutes == 0 and seconds > 0:
        return f"{seconds}s"

    if days > 0:
        return f"{total_seconds}s"

    return str(frequency)


def frequency_to_seconds(frequency: Union[int, str, datetime.timedelta]) -> int:
    """Convert a frequency to seconds.

    Parameters
    ----------
    frequency : int or str or datetime.timedelta
        The frequency to convert.

    Returns
    -------
    int
        Number of seconds.
    """
    result = frequency_to_timedelta(frequency).total_seconds()
    assert int(result) == result, result
    return int(result)


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


def _make_day(day: Optional[Tuple[int, List[int]]]) -> Set[int]:
    """Create a set of days.

    Parameters
    ----------
    day : int or list of int or None
        The day(s) to include in the set.

    Returns
    -------
    set of int
        A set of days.
    """
    if day is None:
        return set(range(1, 32))
    if not isinstance(day, list):
        day = [day]
    return {int(d) for d in day}


def _make_week(week: Optional[Tuple[str, List[str]]]) -> Set[int]:
    """Create a set of weekdays.

    Parameters
    ----------
    week : str or list of str or None
        The weekday(s) to include in the set.

    Returns
    -------
    set of int
        A set of weekdays.
    """
    if week is None:
        return set(range(7))
    if not isinstance(week, list):
        week = [week]
    return {DOW[w.lower()] for w in week}


def _make_months(months: Optional[Union[int, str, List[Union[int, str]]]]) -> Set[int]:
    """Create a set of months.

    Parameters
    ----------
    months : int or str or list of int or str or None
        The month(s) to include in the set.

    Returns
    -------
    set of int
        A set of months.
    """
    if months is None:
        return set(range(1, 13))

    if not isinstance(months, list):
        months = [months]

    return {int(MONTH.get(m, m)) for m in months}


class DateTimes:
    """The DateTimes class is an iterator that generates datetime objects within a given range."""

    def __init__(
        self,
        start: Union[datetime.date, datetime.datetime, str],
        end: Union[datetime.date, datetime.datetime, str],
        increment: int = 24,
        *,
        day_of_month: Optional[Tuple[int, List[int]]] = None,
        day_of_week: Optional[Tuple[str, List[str]]] = None,
        calendar_months: Optional[Union[int, str, List[Union[int, str]]]] = None,
    ):
        """Initialize the DateTimes iterator.

        Parameters
        ----------
        start : datetime.date or datetime.datetime or str
            The start date.
        end : datetime.date or datetime.datetime or str
            The end date.
        increment : int, optional
            The increment in hours, by default 24.
        day_of_month : int or list of int or None, optional
            The day(s) of the month to include, by default None.
        day_of_week : str or list of str or None, optional
            The day(s) of the week to include, by default None.
        calendar_months : int or str or list of int or str or None, optional
            The month(s) to include, by default None.
        """
        self.start = as_datetime(start)
        self.end = as_datetime(end)
        self.increment = frequency_to_timedelta(increment)
        self.day_of_month = _make_day(day_of_month)
        self.day_of_week = _make_week(day_of_week)
        self.calendar_months = _make_months(calendar_months)

    def __iter__(self) -> iter:
        """Iterate over the datetime objects.

        Returns
        -------
        iter
            An iterator of datetime objects.
        """
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

    def __init__(self, year: int, **kwargs):
        """Initialize the Year iterator.

        Parameters
        ----------
        year : int
            The year.
        """
        super().__init__(datetime.datetime(year, 1, 1), datetime.datetime(year, 12, 31), **kwargs)


class Winter(DateTimes):
    """Winter is defined as the months of December, January and February."""

    def __init__(self, year: int, **kwargs):
        """Initialize the Winter iterator.

        Parameters
        ----------
        year : int
            The year.
        """
        super().__init__(
            datetime.datetime(year, 12, 1),
            datetime.datetime(year + 1, 2, calendar.monthrange(year + 1, 2)[1]),
            **kwargs,
        )


class Spring(DateTimes):
    """Spring is defined as the months of March, April and May."""

    def __init__(self, year: int, **kwargs):
        """Initialize the Spring iterator.

        Parameters
        ----------
        year : int
            The year.
        """
        super().__init__(datetime.datetime(year, 3, 1), datetime.datetime(year, 5, 31), **kwargs)


class Summer(DateTimes):
    """Summer is defined as the months of June, July and August."""

    def __init__(self, year: int, **kwargs):
        """Initialize the Summer iterator.

        Parameters
        ----------
        year : int
            The year.
        """
        super().__init__(datetime.datetime(year, 6, 1), datetime.datetime(year, 8, 31), **kwargs)


class Autumn(DateTimes):
    """Autumn is defined as the months of September, October and November."""

    def __init__(self, year: int, **kwargs):
        """Initialize the Autumn iterator.

        Parameters
        ----------
        year : int
            The year.
        """
        super().__init__(datetime.datetime(year, 9, 1), datetime.datetime(year, 11, 30), **kwargs)


class ConcatDateTimes:
    """ConcatDateTimes is an iterator that generates datetime objects from a list of dates."""

    def __init__(self, *dates: DateTimes):
        """Initialize the ConcatDateTimes iterator.

        Parameters
        ----------
        dates : DateTimes
            The list of DateTimes objects.
        """
        if len(dates) == 1 and isinstance(dates[0], list):
            dates = dates[0]

        self.dates = dates

    def __iter__(self) -> iter:
        """Iterate over the datetime objects.

        Returns
        -------
        iter
            An iterator of datetime objects.
        """
        for date in self.dates:
            yield from date


class EnumDateTimes:
    """EnumDateTimes is an iterator that generates datetime objects from a list of dates."""

    def __init__(self, dates: list[Union[datetime.date, datetime.datetime, str]]):
        """Initialize the EnumDateTimes iterator.

        Parameters
        ----------
        dates : list of datetime.date or datetime.datetime or str
            The list of dates.
        """
        self.dates = dates

    def __iter__(self) -> iter:
        """Iterate over the datetime objects.

        Returns
        -------
        iter
            An iterator of datetime objects.
        """
        for date in self.dates:
            yield as_datetime(date)


def datetimes_factory(*args: Any, **kwargs: Any) -> Union[DateTimes, ConcatDateTimes, EnumDateTimes]:
    """Create a DateTimes, ConcatDateTimes, or EnumDateTimes object.

    Parameters
    ----------
    *args : Any
        Positional arguments.
    **kwargs : Any
        Keyword arguments.

    Returns
    -------
    DateTimes or ConcatDateTimes or EnumDateTimes
        The created object.
    """
    if args and kwargs:
        raise ValueError("Cannot provide both args and kwargs for a list of dates")

    if not args and not kwargs:
        raise ValueError("No dates provided")

    if kwargs:
        name = kwargs.get("name")

        if name == "hindcast":
            from .hindcasts import HindcastDatesTimes

            reference_dates = kwargs["reference_dates"]
            reference_dates = datetimes_factory(reference_dates)
            years = kwargs["years"]
            return HindcastDatesTimes(reference_dates=reference_dates, years=years)

        kwargs = kwargs.copy()
        if "frequency" in kwargs:
            kwargs["increment"] = kwargs.pop("frequency")
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


if __name__ == "__main__":
    print(as_datetime_list("R10/2023-01-01T00:00:00Z/P1D"))
    print(as_datetime_list("2007-03-01T13:00:00/2008-05-11T15:30:00", "200h"))
