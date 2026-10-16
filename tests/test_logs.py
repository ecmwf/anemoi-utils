# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging

import pytest

from anemoi.utils.logs import OnceLogger

LOG = logging.getLogger("test_logs")


@pytest.fixture(autouse=True)
def setup(caplog):
    OnceLogger.reset()
    caplog.set_level(logging.DEBUG, logger="test_logs")


def test_logs_once(caplog):
    once = OnceLogger(LOG)
    once.info("x=%s", 1)
    once.info("x=%s", 1)
    once.info(f"x={1}")
    once.info("x=%s", 2)

    assert [r.getMessage() for r in caplog.records] == ["x=1", "x=2"]


def test_levels_are_separate(caplog):
    once = OnceLogger(LOG)
    once.debug("debug")
    once.info("info")
    once.warning("warning")
    once.error("error")

    assert [r.getMessage() for r in caplog.records] == ["debug", "info", "warning", "error"]


def test_reports_caller_location(caplog):
    OnceLogger(LOG).info("msg")

    assert caplog.records[0].funcName == "test_reports_caller_location"
