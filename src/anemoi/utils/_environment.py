# (C) Copyright 2025- Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
from typing import Any


class Environment:
    """Environment variables for Anemoi."""

    ANEMOI_CONFIG_OVERRIDE_PATH: str
    """Path to the configuration override file for Anemoi."""

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Cannot set attributes on Environment class. Use environment variables instead.")

    def __getattr__(self, name: str) -> str | None:
        if name in self.__class__.__annotations__:
            if (env_var := os.getenv(name)) is None:
                return env_var
            try:
                return self.__class__.__annotations__[name](env_var)  # Auto cast
            except Exception as e:
                e.add_note(
                    f"Environment variable {name!r} must be of type {self.__class__.__annotations__[name].__name__}"
                )
                raise e
        raise AttributeError(f"{name} is not a valid environment variable for {self.__class__.__name__}")


ENV = Environment()
