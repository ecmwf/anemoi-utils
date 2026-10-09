# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Logging utilities."""

import contextvars
import logging
import threading

LOGGING_NAME = contextvars.ContextVar("logging_name", default="main")


LOGGER = logging.getLogger(__name__)


def set_logging_name(name: str) -> None:
    """Set the logging name for the current thread.

    Parameters
    ----------
    name : str
        The name to set for logging.
    """
    LOGGING_NAME.set(name)


class ThreadCustomFormatter(logging.Formatter):
    """Custom logging formatter that includes thread-specific logging names."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record to include the thread-specific logging name.

        Parameters
        ----------
        record : logging.LogRecord
            The log record to format.

        Returns
        -------
        str
            The formatted log record.
        """
        record.logging_name = LOGGING_NAME.get()
        return super().format(record)


def enable_logging_name(name: str = "main") -> None:
    """Enable logging with a thread-specific logging name.

    Parameters
    ----------
    name : str, optional
        The default logging name to set, by default "main".
    """

    logger = logging.getLogger()
    is_rich = any(handler.__class__.__name__ == "CustomRichHandler" for handler in logger.handlers)

    set_logging_name(name)

    if is_rich:
        formatter = ThreadCustomFormatter("%(message)s")
    else:
        formatter = ThreadCustomFormatter("%(asctime)s - [%(logging_name)s] - %(levelname)s - %(message)s")

    logger = logging.getLogger()

    for handler in logger.handlers:
        handler.setFormatter(formatter)


def get_rich_handler() -> logging.Handler:
    """Return a RichHandler with custom formatting for logging."""

    from rich.logging import RichHandler
    from rich.text import Text

    class CustomRichHandler(RichHandler):
        def render_message(self, record, message):
            global width

            text = super().render_message(record, message)

            if hasattr(record, "logging_name"):
                name = record.logging_name
                text = Text.assemble(f"[{name}]", (" → ", "dim"), text)

            return text

    return CustomRichHandler(log_time_format="[%X]")


class OnceLogger:
    """Wrap a logger so each distinct message is only emitted once.

    Usage:
    ```python
        logger = logging.getLogger(__name__)
        once_logger = OnceLogger(logger)
        once_logger.info("This message will only be logged once.")
    ```
    """

    _seen = set()
    _lock = threading.Lock()

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def log(self, level: int, message: str, *args, **kwargs) -> None:
        if not self.logger.isEnabledFor(level):
            return
        key = (self.logger.name, level, str(message) % args if args else str(message))
        with self._lock:
            if key in self._seen:
                return
            self._seen.add(key)
        kwargs.setdefault("stacklevel", 2)  # report caller location
        self.logger.log(level, message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        self.log(logging.DEBUG, message, *args, stacklevel=3, **kwargs)

    def info(self, message, *args, **kwargs):
        self.log(logging.INFO, message, *args, stacklevel=3, **kwargs)

    def warning(self, message, *args, **kwargs):
        self.log(logging.WARNING, message, *args, stacklevel=3, **kwargs)

    def error(self, message, *args, **kwargs):
        self.log(logging.ERROR, message, *args, stacklevel=3, **kwargs)

    @classmethod
    def reset(cls) -> None:
        """Forget all messages seen so far (mainly for tests)."""
        with cls._lock:
            cls._seen.clear()
