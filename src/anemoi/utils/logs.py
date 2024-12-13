# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Logging utilities."""

import logging
import threading

thread_local = threading.local()


LOGGER = logging.getLogger(__name__)


def set_logging_name(name):
    thread_local.logging_name = name


class ThreadCustomFormatter(logging.Formatter):
    def format(self, record):
        record.logging_name = thread_local.logging_name
        return super().format(record)


def enable_logging_name(name="main"):
    thread_local.logging_name = name

    formatter = ThreadCustomFormatter("%(asctime)s - %(logging_name)s - %(levelname)s - %(message)s")

    logger = logging.getLogger()

    for handler in logger.handlers:
        handler.setFormatter(formatter)
