# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Generate human readable strings"""

import datetime
import json
import re
import warnings
from collections import defaultdict

from anemoi.utils.dates import as_datetime


def bytes_to_human(n: float) -> str:
    """Convert a number of bytes to a human readable string

    >>> bytes(4096)
    '4 KiB'

    >>> bytes(4000)
    '3.9 KiB'

    Parameters
    ----------
    n : float
        the number of bytes

    Returns
    -------
    str
        a human readable string
    """

    """



    """

    if n < 0:
        sign = "-"
        n -= 0
    else:
        sign = ""

    u = ["", " KiB", " MiB", " GiB", " TiB", " PiB", " EiB", " ZiB", " YiB"]
    i = 0
    while n >= 1024:
        n /= 1024.0
        i += 1
    return "%s%g%s" % (sign, int(n * 10 + 0.5) / 10.0, u[i])


def bytes(n: float) -> str:
    warnings.warn(
        "Function bytes is deprecated and will be removed in a future version. Use bytes_to_human instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return bytes_to_human(n)


def base2_to_human(n) -> str:

    u = ["", "K", "M", "G", "T", " P", "E", "Z", "Y"]
    i = 0
    while n >= 1024:
        n /= 1024.0
        i += 1
    return "%g%s" % (int(n * 10 + 0.5) / 10.0, u[i])


def base2(n) -> str:

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


def _plural(count):
    if count != 1:
        return "s"
    else:
        return ""


def seconds_to_human(seconds: float) -> str:
    """Convert a number of seconds to a human readable string

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
    warnings.warn(
        "Function seconds is deprecated and will be removed in a future version. Use seconds_to_human instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return seconds_to_human(seconds)


def plural(value, what):
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


def __(n):
    if n in (11, 12, 13):
        return "th"

    if n % 10 == 1:
        return "st"

    if n % 10 == 2:
        return "nd"

    if n % 10 == 3:
        return "rd"

    return "th"


def when(then, now=None, short=True, use_utc=False) -> str:
    """Generate a human readable string for a date, relative to now

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
        Genererate shorter strings, by default True
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

        month = then.month
        if now.year != then.year:
            month -= 12

        d = abs(now.month - month)
        if d >= 12:
            return _("a year")
        else:
            return _("%d month%s" % (d, _plural(d)))

    return "on %s %d %s %d" % (
        DOW[then.weekday()],
        then.day,
        MONTH[then.month],
        then.year,
    )


def string_distance(s, t):
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


def did_you_mean(word, vocabulary) -> str:
    """Pick the closest word in a vocabulary

    >>> did_you_mean("aple", ["banana", "lemon", "apple", "orange"])
    'apple'

    Parameters
    ----------
    word : str
        The word to look for
    vocabulary : list of strings
        The list of known words

    Returns
    -------
    str
        The closest word in the vocabulary
    """
    _, best = min((string_distance(word, w), w) for w in vocabulary)
    # if distance < min(len(word), len(best)):
    return best


def dict_to_human(query):
    lst = [f"{k}={v}" for k, v in sorted(query.items())]

    return list_to_human(lst)


def list_to_human(lst, conjunction="and") -> str:
    """Convert a list of strings to a human readable string

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


def human_to_number(value, name, units, none_ok):
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


def as_number(value, name=None, units=None, none_ok=False):
    warnings.warn(
        "Function as_number is deprecated and will be removed in a future version. Use human_to_number instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return human_to_number(value, name, units, none_ok)


def human_seconds(value, name=None, none_ok=False):
    units = dict(s=1, m=60, h=3600, d=86400, w=86400 * 7)
    return human_to_number(value, name, units, none_ok)


def as_seconds(value, name=None, none_ok=False):
    warnings.warn(
        "Function as_seconds is deprecated and will be removed in a future version. Use human_seconds instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return human_seconds(value, name, none_ok)


def human_to_percent(value, name=None, none_ok=False):
    units = {"%": 1}
    return human_to_number(value, name, units, none_ok)


def as_percent(value, name=None, none_ok=False):
    warnings.warn(
        "Function as_percent is deprecated and will be removed in a future version. Use human_to_percent instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return human_to_percent(value, name, none_ok)


def human_to_bytes(value, name=None, none_ok=False):
    units = {}
    n = 1
    for u in "KMGTP":
        n *= 1024
        units[u] = n
        units[u.lower()] = n

    return human_to_number(value, name, units, none_ok)


def as_bytes(value, name=None, none_ok=False):
    warnings.warn(
        "Function as_bytes is deprecated and will be removed in a future version. Use human_to_bytes instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return human_to_bytes(value, name, none_ok)


def human_to_timedelta(value, name=None, none_ok=False):
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


def as_timedelta(value, name=None, none_ok=False):
    warnings.warn(
        "Function as_timedelta is deprecated and will be removed in a future version. Use human_to_timedelta instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return human_to_timedelta(value, name, none_ok)


def rounded_datetime(d):
    if float(d.microsecond) / 1000.0 / 1000.0 >= 0.5:
        d = d + datetime.timedelta(seconds=1)
    d = d.replace(microsecond=0)
    return d


def json_pretty_dump(obj, max_line_length=120, default=str) -> str:
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

    def _format_json(obj, indent_level=0):
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


def shorten_list(lst, max_length=5) -> list:
    """Shorten a list to a maximum length.

    Parameters
    ----------
    lst : list
        The list to be shortened.
    max_length : int, optional
        Maximum length of the shortened list. Default is 5.

    Returns
    -------
    list
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


def _compress_dates(dates):
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


def compress_dates(dates) -> str:
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


def print_dates(dates) -> None:
    """Print a list of dates in a human-readable format.

    Parameters
    ----------
    dates : list
        A list of dates, as datetime objects or strings.
    """
    print(compress_dates(dates))
