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
import time
from collections import defaultdict

from .humanize import seconds_to_human

LOGGER = logging.getLogger(__name__)


class Timer:
    """Context manager to measure elapsed time."""

    def __init__(self, title, logger=LOGGER):
        self.title = title
        self.start = time.time()
        self.logger = logger

    def __enter__(self):
        return self

    @property
    def elapsed(self):
        return time.time() - self.start

    def __exit__(self, *args):
        self.logger.info("%s: %s.", self.title, seconds_to_human(self.elapsed))


class _Timer:
    """Internal timer class."""

    def __init__(self):
        self.elapsed = 0.0

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def start(self):
        self._start = time.time()

    def stop(self):
        self.elapsed += time.time() - self._start


class Timers:
    """A collection of timers."""

    def __init__(self, logger=LOGGER):
        self.logger = logger
        self.timers = defaultdict(_Timer)

    def __getitem__(self, name):
        return self.timers[name]

    def report(self):
        length = max(len(name) for name in self.timers)
        for name, timer in sorted(self.timers.items()):
            self.logger.info("%s: %s.", f"{name:<{length}}", seconds_to_human(timer.elapsed))
