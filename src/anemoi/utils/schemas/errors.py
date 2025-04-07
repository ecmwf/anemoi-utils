# (C) Copyright 2025 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ValidationError
from pydantic_core import ErrorDetails

CUSTOM_MESSAGES = {
    "missing": "A config entry seems to be missing. If not please check for any typos.",
    "extra_forbidden": "Extra entries in the config are forebidden. Please check for typos.",
}


def convert_errors(e: ValidationError, custom_messages: dict[str, str]) -> list[ErrorDetails]:
    new_errors: list[ErrorDetails] = []
    for error in e.errors():
        custom_message = custom_messages.get(error["type"])

        if custom_message:

            ctx = error.get("ctx")
            error["msg"] = custom_message.format(**ctx) if ctx else custom_message
        new_errors.append(error)
    return new_errors


class ValidationError(Exception):
    pass


def allowed_values(v: Any, values: list[Any]) -> Any:
    if v not in values:
        msg = {f"Value {v} not in {values}"}
        raise ValidationError(msg)
    return v


def required_fields(model: type[PydanticBaseModel], recursive: bool = False) -> Iterator[str]:
    for name, field in model.model_fields.items():
        if not field.is_required():
            continue
        t = field.annotation
        if recursive and isinstance(t, type) and issubclass(t, PydanticBaseModel):
            yield from required_fields(t, recursive=True)
        else:
            yield name
