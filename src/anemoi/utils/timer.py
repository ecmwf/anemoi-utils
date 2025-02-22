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
    """Context manager to measure elapsed time.

    Parameters
    ----------
    title : str
        The title of the timer.
    logger : logging.Logger, optional
        The logger to use for logging the elapsed time, by default LOGGER.
    """

    def __init__(self, title: str, logger: logging.Logger = LOGGER):
        """Initialize the Timer.

        Parameters
        ----------
        title : str
            The title of the timer.
        logger : logging.Logger, optional
            The logger to use for logging the elapsed time, by default LOGGER.
        """
        self.title = title
        self.start = time.time()
        self.logger = logger

    def __enter__(self) -> "Timer":
        """Enter the runtime context related to this object.

        Returns
        -------
        Timer
            The Timer object itself.
        """
        return self

    @property
    def elapsed(self) -> float:
        """Float: The elapsed time in seconds."""
        return time.time() - self.start

    def __exit__(self, *args: Any) -> None:
        """Exit the runtime context related to this object.

        Parameters
        ----------
        *args : Any
            Exception information.
        """
        self.logger.info("%s: %s.", self.title, seconds_to_human(self.elapsed))


class _Timer:
    """Internal timer class."""

    def __init__(self):
        """Initialize the _Timer."""
        self.elapsed = 0.0

    def __enter__(self) -> "_Timer":
        """Enter the runtime context related to this object.

        Returns
        -------
        _Timer
            The _Timer object itself.
        """
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit the runtime context related to this object.

        Parameters
        ----------
        *args : Any
            Exception information.
        """
        self.stop()

    def start(self) -> None:
        """Start the timer."""
        self._start = time.time()

    def stop(self) -> None:
        """Stop the timer and accumulate the elapsed time."""
        self.elapsed += time.time() - self._start


class Timers:
    """A collection of timers.

    Parameters
    ----------
    logger : logging.Logger, optional
        The logger to use for logging the elapsed time, by default LOGGER.
    """

    def __init__(self, logger: logging.Logger = LOGGER):
        """Initialize the Timers collection.

        Parameters
        ----------
        logger : logging.Logger, optional
            The logger to use for logging the elapsed time, by default LOGGER.
        """
        self.logger = logger
        self.timers = defaultdict(_Timer)

    def __getitem__(self, name: str) -> _Timer:
        """Get a timer by name.

        Parameters
        ----------
        name : str
            The name of the timer.

        Returns
        -------
        _Timer
            The timer with the given name.
        """
        return self.timers[name]

    def report(self) -> None:
        """Log the elapsed time for all timers."""
        length = max(len(name) for name in self.timers)
        for name, timer in sorted(self.timers.items()):
            self.logger.info("%s: %s.", f"{name:<{length}}", seconds_to_human(timer.elapsed))
