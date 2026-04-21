# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime

import pytest

from anemoi.utils.humanize import make_list_int
from anemoi.utils.humanize import when

UTC = datetime.timezone.utc

# Fixed reference points
NOW_NAIVE = datetime.datetime(2024, 6, 15, 12, 0, 0)
NOW_AWARE = datetime.datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


# -----------------------
# Timezone-mismatch tests
# -----------------------


def test_when_use_utc_naive_then():
    """The original crash: use_utc=True auto-generates an aware `now`; naive `then` must be normalised."""
    then_naive = datetime.datetime(2024, 6, 15, 10, 0, 0)  # naive, 2 h before NOW_AWARE
    result = when(then_naive, use_utc=True)
    assert "ago" in result


def test_when_no_utc_aware_then():
    """use_utc=False (default) with an aware `then` should strip tzinfo and not raise."""
    then_aware = NOW_NAIVE.replace(tzinfo=UTC) - datetime.timedelta(hours=2)
    result = when(then_aware, now=NOW_NAIVE)
    assert result == "2 hours ago"


def test_when_use_utc_aware_then():
    """use_utc=True with an already UTC-aware `then` should work as before."""
    then_aware = NOW_AWARE - datetime.timedelta(hours=2)
    result = when(then_aware, now=NOW_AWARE, use_utc=True)
    assert result == "2 hours ago"


def test_when_both_naive():
    """Baseline: both datetimes naive should continue to work."""
    then = NOW_NAIVE - datetime.timedelta(hours=2)
    result = when(then, now=NOW_NAIVE)
    assert result == "2 hours ago"


def test_when_both_aware_utc():
    """Baseline: both datetimes UTC-aware should continue to work."""
    then = NOW_AWARE - datetime.timedelta(hours=3)
    result = when(then, now=NOW_AWARE, use_utc=True)
    assert result == "3 hours ago"


# ---------------------------------------------------------------------------
# Return-value tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "delta, expected",
    [
        (datetime.timedelta(seconds=0), "right now"),
        (datetime.timedelta(seconds=30), "30 seconds ago"),
        (datetime.timedelta(minutes=5), "5 minutes ago"),
        (datetime.timedelta(hours=2), "2 hours ago"),
    ],
)
def test_when_past_values(delta, expected):
    """when() returns the correct human-readable string for past datetimes."""
    then = NOW_NAIVE - delta
    assert when(then, now=NOW_NAIVE) == expected


@pytest.mark.parametrize(
    "delta, expected",
    [
        (datetime.timedelta(seconds=30), "in 30 seconds"),
        (datetime.timedelta(minutes=5), "in 5 minutes"),
        (datetime.timedelta(hours=2), "in 2 hours"),
    ],
)
def test_when_future_values(delta, expected):
    """when() returns the correct human-readable string for future datetimes."""
    then = NOW_NAIVE + delta
    assert when(then, now=NOW_NAIVE) == expected


# ---------------------------------------------------------------------------
# make_list_int tests
# ---------------------------------------------------------------------------


def test_make_list_int_single_int():
    assert make_list_int(42) == [42]


def test_make_list_int_list_passthrough():
    assert make_list_int([1, 2, 3]) == [1, 2, 3]


def test_make_list_int_tuple():
    assert make_list_int((1, 2, 3)) == [1, 2, 3]


def test_make_list_int_single_string():
    assert make_list_int("5") == [5]


def test_make_list_int_slash_separated():
    assert make_list_int("1/2/3") == [1, 2, 3]


def test_make_list_int_to_range():
    assert make_list_int("0/to/6") == [0, 1, 2, 3, 4, 5, 6]


def test_make_list_int_to_range_inclusive_end():
    """End value must be included even when it falls exactly on a step boundary."""
    assert make_list_int("0/to/24") == list(range(0, 25))


def test_make_list_int_to_by_range():
    assert make_list_int("0/to/24/by/6") == [0, 6, 12, 18, 24]


def test_make_list_int_to_by_inclusive_end():
    """End value must be included when it falls exactly on a step boundary (bug fix)."""
    assert make_list_int("0/to/12/by/6") == [0, 6, 12]


def test_make_list_int_to_by_non_divisible_end():
    """End value is not included when it does not fall on a step boundary."""
    assert make_list_int("0/to/10/by/3") == [0, 3, 6, 9]


def test_make_list_int_to_by_case_insensitive():
    assert make_list_int("0/TO/12/BY/6") == [0, 6, 12]


def test_make_list_int_invalid_raises():
    with pytest.raises((ValueError, TypeError)):
        make_list_int({"a": 1})
