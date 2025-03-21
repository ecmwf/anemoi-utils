# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Generate human readable strings."""

import datetime
import json
import re
import warnings
from collections import defaultdict
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from anemoi.utils.dates import as_datetime


def bytes_to_human(n: float) -> str:
    """Convert a number of bytes to a human readable string.

    >>> bytes_to_human(4096)
    '4 KiB'

    >>> bytes_to_human(4000)
    '3.9 KiB'

    Parameters
    ----------
    n : float
        The number of bytes

    Returns
    -------
    str
        A human readable string
    """
    if n < 0:
        sign = "-"
        n = -n
    else:
        sign = ""

    u = ["", " KiB", " MiB", " GiB", " TiB", " PiB", " EiB", " ZiB", " YiB"]
    i = 0
    while n >= 1024:
        n /= 1024.0
        i += 1
    return "%s%g%s" % (sign, int(n * 10 + 0.5) / 10.0, u[i])


def bytes(n: float) -> str:
    """Deprecated function to convert bytes to a human readable string.

    Parameters
    ----------
    n : float
        The number of bytes

    Returns
    -------
    str
        A human readable string
    """
    warnings.warn(
        "Function bytes is deprecated and will be removed in a future version. Use bytes_to_human instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return bytes_to_human(n)


def base2_to_human(n: float) -> str:
    """Convert a number to a human readable string using base 2 units.

    Parameters
    ----------
    n : float
        The number to convert

    Returns
    -------
    str
        A human readable string
    """
    u = ["", "K", "M", "G", "T", " P", "E", "Z", "Y"]
    i = 0
    while n >= 1024:
        n /= 1024.0
        i += 1
    return "%g%s" % (int(n * 10 + 0.5) / 10.0, u[i])


def base2(n: float) -> str:
    """Deprecated function to convert a number to a human readable string using base 2 units.

    Parameters
    ----------
    n : float
        The number to convert

    Returns
    -------
    str
        A human readable string
    """
    warnings.warn(
        "Function base2 is deprecated and will be removed in a future version. Use base2_to_human instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return base2_to_human(n)


PERIODS = (
    (7 * 24 * 60 * 60, "week"),
    (24 * 60 * 60, "day"),
    (60 * 60, "hour"),
    (60, "minute"),
    (1, "second"),
)


def _plural(count: int) -> str:
    """Return 's' if count is not 1, otherwise return an empty string.

    Parameters
    ----------
    count : int
        The count

    Returns
    -------
    str
        's' if count is not 1, otherwise an empty string
    """
    if count != 1:
        return "s"
    else:
        return ""


def seconds_to_human(seconds: Union[float, datetime.timedelta]) -> str:
    """Convert a number of seconds to a human readable string.

    >>> seconds_to_human(4000)
    '1 hour 6 minutes 40 seconds'

    Parameters
    ----------
    seconds : float
        The number of seconds

    Returns
    -------
    str
        A human readable string
    """
    if isinstance(seconds, datetime.timedelta):
        seconds = seconds.total_seconds()

    if seconds == 0:
        return "instantaneous"

    if seconds < 0.1:
        units = [
            None,
            "milli",
            "micro",
            "nano",
            "pico",
            "femto",
            "atto",
            "zepto",
            "yocto",
        ]
        i = 0
        while seconds < 1.0 and i < len(units) - 1:
            seconds *= 1000
            i += 1
        if seconds > 100 and i > 0:
            seconds /= 1000
            i -= 1
        seconds = round(seconds * 10) / 10
        return f"{seconds:g} {units[i]}second{_plural(seconds)}"

    n = seconds
    s = []
    for p in PERIODS:
        m = int(n / p[0])
        if m:
            s.append("%d %s%s" % (m, p[1], _plural(m)))
            n %= p[0]

    if not s:
        seconds = round(seconds * 10) / 10
        s.append("%g second%s" % (seconds, _plural(seconds)))
    return " ".join(s)


def seconds(seconds: float) -> str:
    """Deprecated function to convert seconds to a human readable string.

    Parameters
    ----------
    seconds : float
        The number of seconds

    Returns
    -------
    str
        A human readable string
    """
    warnings.warn(
        "Function seconds is deprecated and will be removed in a future version. Use seconds_to_human instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return seconds_to_human(seconds)


def plural(value: int, what: str) -> str:
    """Return a string with the value and the pluralized form of what.

    Parameters
    ----------
    value : int
        The value
    what : str
        The string to pluralize

    Returns
    -------
    str
        The value and the pluralized form of what
    """
    return f"{value:,} {what}{_plural(value)}"


DOW = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

MONTH = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def __(n: int) -> str:
    """Return the ordinal suffix for a number.

    Parameters
    ----------
    n : int
        The number

    Returns
    -------
    str
        The ordinal suffix
    """
    if n in (11, 12, 13):
        return "th"

    if n % 10 == 1:
        return "st"

    if n % 10 == 2:
        return "nd"

    if n % 10 == 3:
        return "rd"

    return "th"


def when(
    then: datetime.datetime, now: Optional[datetime.datetime] = None, short: bool = True, use_utc: bool = False
) -> str:
    """Generate a human readable string for a date, relative to now.

    >>> when(datetime.datetime.now() - datetime.timedelta(hours=2))
    '2 hours ago'

    >>> when(datetime.datetime.now() - datetime.timedelta(days=1))
    'yesterday at 08:46'

    >>> when(datetime.datetime.now() - datetime.timedelta(days=5))
    'last Sunday'

    >>> when(datetime.datetime.now() - datetime.timedelta(days=365))
    'last year'

    >>> when(datetime.datetime.now() + datetime.timedelta(days=365))
    'next year'

    Parameters
    ----------
    then : datetime.datetime
        A datetime
    now : datetime.datetime, optional
        The reference date, by default NOW
    short : bool, optional
        Generate shorter strings, by default True
    use_utc : bool, optional
        Use UTC time, by default False

    Returns
    -------
    str
        A human readable string
    """
    last = "last"

    if now is None:
        if use_utc:
            now = datetime.datetime.utcnow()
        else:
            now = datetime.datetime.now()

    diff = (now - then).total_seconds()

    if diff < 0:
        last = "next"
        diff = -diff

    diff = int(diff)

    if diff == 0:
        return "right now"

    def _(x):
        if last == "last":
            return "%s ago" % (x,)
        else:
            return "in %s" % (x,)

    if diff < 60:
        diff = int(diff + 0.5)
        return _("%s second%s" % (diff, _plural(diff)))

    if diff < 60 * 60:
        diff /= 60
        diff = int(diff + 0.5)
        return _("%s minute%s" % (diff, _plural(diff)))

    if diff < 60 * 60 * 6:
        diff /= 60 * 60
        diff = int(diff + 0.5)
        return _("%s hour%s" % (diff, _plural(diff)))

    jnow = now.toordinal()
    jthen = then.toordinal()

    if jnow == jthen:
        return "today at %02d:%02d" % (then.hour, then.minute)

    if jnow == jthen + 1:
        return "yesterday at %02d:%02d" % (then.hour, then.minute)

    if jnow == jthen - 1:
        return "tomorrow at %02d:%02d" % (then.hour, then.minute)

    if abs(jnow - jthen) <= 7:
        if last == "next":
            last = "this"
        return "%s %s" % (
            last,
            DOW[then.weekday()],
        )

    if abs(jnow - jthen) < 32 and now.month == then.month:
        return "the %d%s of this month" % (then.day, __(then.day))

    if abs(jnow - jthen) < 64 and now.month == then.month + 1:
        return "the %d%s of %s month" % (then.day, __(then.day), last)

    if short:
        years = int(abs(jnow - jthen) / 365.25 + 0.5)
        if years == 1:
            return "%s year" % last

        if years > 1:
            return _("%d years" % (years,))

        delta = abs(now - then)
        if delta.days > 1 and delta.days < 30:
            return _("%d days" % (delta.days,))

    return "on %s %d %s %d" % (
        DOW[then.weekday()],
        then.day,
        MONTH[then.month],
        then.year,
    )


def string_distance(s: str, t: str) -> int:
    """Calculate the Levenshtein distance between two strings.

    Parameters
    ----------
    s : str
        The first string
    t : str
        The second string

    Returns
    -------
    int
        The Levenshtein distance
    """
    import numpy as np

    m = len(s)
    n = len(t)
    d = np.zeros((m + 1, n + 1), dtype=int)

    one = int(1)
    zero = int(0)

    d[:, 0] = np.arange(m + 1)
    d[0, :] = np.arange(n + 1)

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = zero if s[i - 1] == t[j - 1] else one
            d[i, j] = min(
                d[i - 1, j] + one,
                d[i, j - 1] + one,
                d[i - 1, j - 1] + cost,
            )

    return d[m, n]


def did_you_mean(word: str, vocabulary: List[str]) -> str:
    """Pick the closest word in a vocabulary.

    >>> did_you_mean("aple", ["banana", "lemon", "apple", "orange"])
    'apple'

    Parameters
    ----------
    word : str
        The word to look for
    vocabulary : list of str
        The list of known words

    Returns
    -------
    str
        The closest word in the vocabulary
    """
    _, best = min((string_distance(word, w), w) for w in vocabulary)
    # if distance < min(len(word), len(best)):
    return best


def dict_to_human(query: Dict[str, Any]) -> str:
    """Convert a dictionary to a human readable string.

    Parameters
    ----------
    query : dict
        The dictionary to convert

    Returns
    -------
    str
        A human readable string
    """
    lst = [f"{k}={v}" for k, v in sorted(query.items())]

    return list_to_human(lst)


def list_to_human(lst: List[str], conjunction: str = "and") -> str:
    """Convert a list of strings to a human readable string.

    >>> list_to_human(["banana", "lemon", "apple", "orange"])
    'banana, lemon, apple and orange'

    Parameters
    ----------
    lst : list of str
        The list of strings to concatenate
    conjunction : str, optional
        The word to connect the last word in the list (like "or" or "and"), by default "and"

    Returns
    -------
    str
        Human readable string of list
    """
    if not lst:
        return "??"

    if len(lst) > 2:
        lst = [", ".join(lst[:-1]), lst[-1]]

    return f" {conjunction} ".join(lst)


def human_to_number(value: Union[str, int], name: str, units: Dict[str, int], none_ok: bool) -> Optional[int]:
    """Convert a human readable string to a number.

    Parameters
    ----------
    value : str or int
        The value to convert
    name : str
        The name of the value
    units : dict
        The units to use for conversion
    none_ok : bool
        Whether None is an acceptable value

    Returns
    -------
    int or None
        The converted value
    """
    if value is None and none_ok:
        return None

    value = str(value)
    # TODO: support floats
    m = re.search(r"^\s*(\d+)\s*([%\w]+)?\s*$", value)
    if m is None:
        raise ValueError(f"{name}: invalid number/unit {value}")
    value = int(m.group(1))
    if m.group(2) is None:
        return value
    unit = m.group(2)[0]
    if unit not in units:
        valid = ", ".join(units.keys())
        raise ValueError(f"{name}: invalid unit '{unit}', valid values are {valid}")
    return value * units[unit]


def as_number(
    value: Union[str, int], name: Optional[str] = None, units: Optional[Dict[str, int]] = None, none_ok: bool = False
) -> Optional[int]:
    """Deprecated function to convert a human readable string to a number.

    Parameters
    ----------
    value : str or int
        The value to convert
    name : str, optional
        The name of the value
    units : dict, optional
        The units to use for conversion
    none_ok : bool, optional
        Whether None is an acceptable value

    Returns
    -------
    int or None
        The converted value
    """
    warnings.warn(
        "Function as_number is deprecated and will be removed in a future version. Use human_to_number instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return human_to_number(value, name, units, none_ok)


def human_seconds(value: Union[str, int], name: Optional[str] = None, none_ok: bool = False) -> Optional[int]:
    """Convert a human readable string to seconds.

    Parameters
    ----------
    value : str or int
        The value to convert
    name : str, optional
        The name of the value
    none_ok : bool, optional
        Whether None is an acceptable value

    Returns
    -------
    int or None
        The converted value in seconds
    """
    units = dict(s=1, m=60, h=3600, d=86400, w=86400 * 7)
    return human_to_number(value, name, units, none_ok)


def as_seconds(value: Union[str, int], name: Optional[str] = None, none_ok: bool = False) -> Optional[int]:
    """Deprecated function to convert a human readable string to seconds.

    Parameters
    ----------
    value : str or int
        The value to convert
    name : str, optional
        The name of the value
    none_ok : bool, optional
        Whether None is an acceptable value

    Returns
    -------
    int or None
        The converted value in seconds
    """
    warnings.warn(
        "Function as_seconds is deprecated and will be removed in a future version. Use human_seconds instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return human_seconds(value, name, none_ok)


def human_to_percent(value: Union[str, int], name: Optional[str] = None, none_ok: bool = False) -> Optional[int]:
    """Convert a human readable string to a percentage.

    Parameters
    ----------
    value : str or int
        The value to convert
    name : str, optional
        The name of the value
    none_ok : bool, optional
        Whether None is an acceptable value

    Returns
    -------
    int or None
        The converted value in percentage
    """
    units = {"%": 1}
    return human_to_number(value, name, units, none_ok)


def as_percent(value: Union[str, int], name: Optional[str] = None, none_ok: bool = False) -> Optional[int]:
    """Deprecated function to convert a human readable string to a percentage.

    Parameters
    ----------
    value : str or int
        The value to convert
    name : str, optional
        The name of the value
    none_ok : bool, optional
        Whether None is an acceptable value

    Returns
    -------
    int or None
        The converted value in percentage
    """
    warnings.warn(
        "Function as_percent is deprecated and will be removed in a future version. Use human_to_percent instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return human_to_percent(value, name, none_ok)


def human_to_bytes(value: Union[str, int], name: Optional[str] = None, none_ok: bool = False) -> Optional[int]:
    """Convert a human readable string to bytes.

    Parameters
    ----------
    value : str or int
        The value to convert
    name : str, optional
        The name of the value
    none_ok : bool, optional
        Whether None is an acceptable value

    Returns
    -------
    int or None
        The converted value in bytes
    """
    units = {}
    n = 1
    for u in "KMGTP":
        n *= 1024
        units[u] = n
        units[u.lower()] = n

    return human_to_number(value, name, units, none_ok)


def as_bytes(value: Union[str, int], name: Optional[str] = None, none_ok: bool = False) -> Optional[int]:
    """Deprecated function to convert a human readable string to bytes.

    Parameters
    ----------
    value : str or int
        The value to convert
    name : str, optional
        The name of the value
    none_ok : bool, optional
        Whether None is an acceptable value

    Returns
    -------
    int or None
        The converted value in bytes
    """
    warnings.warn(
        "Function as_bytes is deprecated and will be removed in a future version. Use human_to_bytes instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return human_to_bytes(value, name, none_ok)


def human_to_timedelta(value: str, name: Optional[str] = None, none_ok: bool = False) -> datetime.timedelta:
    """Convert a human readable string to a timedelta.

    Parameters
    ----------
    value : str
        The value to convert
    name : str, optional
        The name of the value
    none_ok : bool, optional
        Whether None is an acceptable value

    Returns
    -------
    datetime.timedelta
        The converted value as a timedelta
    """
    if value is None and none_ok:
        return None

    save = value
    value = re.sub(r"[^a-zA-Z0-9]", "", value.lower())
    value = re.sub(r"([a-zA-Z])[a-zA-Z]*", r"\1", value)
    # value = re.sub(r"[^dmhsw0-9]", "", value)
    bits = [b for b in re.split(r"([dmhsw])", value) if b != ""]

    times = defaultdict(int)

    val = None

    for i, n in enumerate(bits):
        if i % 2 == 0:
            val = int(n)
        else:
            assert n in ("d", "m", "h", "s", "w")
            times[n] = val
            val = None

    if val is not None:
        if name:
            raise ValueError(f"{name}: invalid period '{save}'")
        raise ValueError(f"Invalid period '{save}'")

    return datetime.timedelta(
        weeks=times["w"],
        days=times["d"],
        hours=times["h"],
        minutes=times["m"],
        seconds=times["s"],
    )


def as_timedelta(value: str, name: Optional[str] = None, none_ok: bool = False) -> datetime.timedelta:
    """Deprecated function to convert a human readable string to a timedelta.

    Parameters
    ----------
    value : str
        The value to convert
    name : str, optional
        The name of the value
    none_ok : bool, optional
        Whether None is an acceptable value

    Returns
    -------
    datetime.timedelta
        The converted value as a timedelta
    """
    warnings.warn(
        "Function as_timedelta is deprecated and will be removed in a future version. Use human_to_timedelta instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return human_to_timedelta(value, name, none_ok)


def rounded_datetime(d: datetime.datetime) -> datetime.datetime:
    """Round a datetime to the nearest second.

    Parameters
    ----------
    d : datetime.datetime
        The datetime to round

    Returns
    -------
    datetime.datetime
        The rounded datetime
    """
    if float(d.microsecond) / 1000.0 / 1000.0 >= 0.5:
        d = d + datetime.timedelta(seconds=1)
    d = d.replace(microsecond=0)
    return d


def json_pretty_dump(obj: Any, max_line_length: int = 120, default: Callable = str) -> str:
    """Custom JSON dump function that keeps dicts and lists on one line if they are short enough.

    Parameters
    ----------
    obj : Any
        The object to be dumped as JSON.
    max_line_length : int, optional
        Maximum allowed line length for pretty-printing. Default is 120.
    default : function, optional
        Default function to convert non-serializable objects. Default is str.

    Returns
    -------
    str
        JSON string.
    """

    def _format_json(obj: Any, indent_level: int = 0) -> str:
        """Helper function to format JSON objects with custom pretty-print rules.

        Parameters
        ----------
        obj : Any
            The object to format.
        indent_level : int, optional
            Current indentation level. Default is 0.

        Returns
        -------
        str
            Formatted JSON string.
        """
        indent = " " * 4 * indent_level
        if isinstance(obj, dict):
            items = []
            for key, value in obj.items():
                items.append(f'"{key}": {_format_json(value, indent_level + 1)}')
            line = "{" + ", ".join(items) + "}"
            if len(line) <= max_line_length:
                return line
            else:
                return "{\n" + ",\n".join([f"{indent}    {item}" for item in items]) + "\n" + indent + "}"
        elif isinstance(obj, list):
            items = [_format_json(item, indent_level + 1) for item in obj]
            line = "[" + ", ".join(items) + "]"
            if len(line) <= max_line_length:
                return line
            else:
                return "[\n" + ",\n".join([f"{indent}    {item}" for item in items]) + "\n" + indent + "]"
        else:
            return json.dumps(obj, default=default)

    return _format_json(obj)


def shorten_list(lst: Union[List[Any], Tuple[Any]], max_length: int = 5) -> Union[List[Any], Tuple[Any]]:
    """Shorten a list to a maximum length.

    Parameters
    ----------
    lst : list or tuple
        The list to be shortened.
    max_length : int, optional
        Maximum length of the shortened list. Default is 5.

    Returns
    -------
    list or tuple
        Shortened list.
    """
    if len(lst) <= max_length:
        return lst
    else:
        half = max_length // 2
        result = list(lst[:half]) + ["..."] + list(lst[max_length - half :])
        if isinstance(lst, tuple):
            return tuple(result)
        return result


def _compress_dates(
    dates: List[datetime.datetime],
) -> Generator[
    Union[List[datetime.datetime], Tuple[datetime.datetime, datetime.datetime, datetime.timedelta]], None, None
]:
    """Compress a list of dates into a more compact representation.

    Parameters
    ----------
    dates : list of datetime.datetime
        The list of dates to compress

    Returns
    -------
    list or tuple
        The compressed dates
    """
    dates = sorted(dates)
    if len(dates) < 3:
        yield dates
        return

    prev = first = dates.pop(0)
    curr = dates.pop(0)
    delta = curr - prev
    while curr - prev == delta:
        prev = curr
        if not dates:
            break
        curr = dates.pop(0)

    yield (first, prev, delta)
    if dates:
        yield from _compress_dates([curr] + dates)


def compress_dates(dates: List[Union[datetime.datetime, str]]) -> str:
    """Compress a list of dates into a human-readable format.

    Parameters
    ----------
    dates : list
        A list of dates, as datetime objects or strings.

    Returns
    -------
    str
        A human-readable string representing the compressed dates.
    """

    dates = [as_datetime(_) for _ in dates]
    result = []

    for n in _compress_dates(dates):
        if isinstance(n, list):
            result.extend([str(_) for _ in n])
        else:
            result.append(" ".join([str(n[0]), "to", str(n[1]), "by", str(n[2])]))

    return result


def print_dates(dates: List[Union[datetime.datetime, str]]) -> None:
    """Print a list of dates in a human-readable format.

    Parameters
    ----------
    dates : list
        A list of dates, as datetime objects or strings.
    """
    print(compress_dates(dates))


def make_list_int(value: Union[str, List[int], Tuple[int], int]) -> List[int]:
    """Convert a string like "1/2/3" or "1/to/3" or "1/to/10/by/2" to a list of integers.

    Parameters
    ----------
    value : str, list, tuple, int
        The value to convert to a list of integers.

    Returns
    -------
    list
        A list of integers.
    """
    if isinstance(value, str):
        if "/" not in value:
            return [int(value)]
        bits = value.split("/")
        if len(bits) == 3 and bits[1].lower() == "to":
            value = list(range(int(bits[0]), int(bits[2]) + 1, 1))

        elif len(bits) == 5 and bits[1].lower() == "to" and bits[3].lower() == "by":
            value = list(range(int(bits[0]), int(bits[2]) + int(bits[4]), int(bits[4])))

    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return value
    if isinstance(value, int):
        return [value]

    raise ValueError(f"Cannot make list from {value}")
