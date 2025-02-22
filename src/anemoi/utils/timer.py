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
from typing import Any

from .humanize import seconds_to_human

LOGGER = logging.getLogger(__name__)


class Timer:
    """Context manager to measure elapsed time."""

    def __init__(self, title: str, logger: logging.Logger = LOGGER):
        self.title = title
        self.start = time.time()
        self.logger = logger

    def __enter__(self) -> "Timer":
        return self

    @property
    def elapsed(self) -> float:
        return time.time() - self.start

    def __exit__(self, *args: Any):
        self.logger.info("%s: %s.", self.title, seconds_to_human(self.elapsed))


class _Timer:
    """Internal timer class."""

    def __init__(self):
        self.elapsed = 0.0

    def __enter__(self) -> "_Timer":
        self.start()
        return self

    def __exit__(self, *args: Any):
        self.stop()

    def start(self) -> None:
        self._start = time.time()

    def stop(self) -> None:
        self.elapsed += time.time() - self._start


class Timers:
    """A collection of timers."""

    def __init__(self, logger: logging.Logger = LOGGER):
        self.logger = logger
        self.timers = defaultdict(_Timer)

    def __getitem__(self, name: str) -> _Timer:
        return self.timers[name]

    def report(self) -> None:
        length = max(len(name) for name in self.timers)
        for name, timer in sorted(self.timers.items()):
            self.logger.info("%s: %s.", f"{name:<{length}}", seconds_to_human(timer.elapsed))
