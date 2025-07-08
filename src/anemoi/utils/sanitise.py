# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.parse import urlunparse

# Patterns used by earthkit-data for url-patterns and path-patterns

RE1 = re.compile(r"{([^}]*)}")  # {*}
RE2 = re.compile(r"\(([^}]*)\)")  # (*)


def sanitise(obj: Any, level=1) -> Any:
    """Sanitise an object by replacing all full paths with shortened versions and URL credentials with '***'.

    Parameters
    ----------
    obj : Any
        The object to sanitise.
    level : int, optional
        The level of sanitation. The higher levels will also apply the levels below it.
        - 1: Shorten file paths to file name and hide credentials in URLs (default).
        - 2: Hide hostnames in URLs.
        - 3: Hide full file paths and URLs.

    Returns
    -------
    Any
        The sanitised object.
    """

    assert level in (1, 2, 3), "level must be 1, 2 or 3"

    if isinstance(obj, dict):
        return {sanitise(k): sanitise(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [sanitise(v) for v in obj]

    if isinstance(obj, tuple):
        return tuple(sanitise(v) for v in obj)

    if isinstance(obj, str):
        return _sanitise_string(obj, level)

    return obj


def _sanitise_string(obj: str, level=1) -> str:
    """Sanitise a string by replacing full paths and URL passwords."""

    parsed = urlparse(obj, allow_fragments=True)

    if parsed.scheme and parsed.scheme[0].isalpha():
        return _sanitise_url(parsed, level)

    if level > 2:
        return "hidden"

    if obj.startswith("/") or obj.startswith("~"):
        return _sanitise_path(obj)

    return obj


def _sanitise_url(parsed: Any, level=1) -> str:
    """Sanitise a URL by replacing passwords with '***'."""

    LIST = [
        "pass",
        "password",
        "token",
        "user",
        "key",
        "pwd",
        "_key",
        "_token",
        "apikey",
        "api_key",
        "api_token",
        "_api_token",
        "_api_key",
        "username",
        "login",
        "auth",
        "auth_token",
        "auth_key",
    ]

    scheme, netloc, path, params, query, fragment = parsed

    if parsed.password or parsed.username:
        _, host = netloc.split("@")
        user = "user:***" if parsed.password else "user"
        netloc = f"{user}@{host}"

    if query:
        qs = parse_qs(query)
        for k in LIST:
            if k in qs:
                qs[k] = "hidden"
        query = urlencode(qs, doseq=True)

    if params:
        qs = parse_qs(params)
        for k in LIST:
            if k in qs:
                qs[k] = "hidden"
        params = urlencode(qs, doseq=True)

    if level > 1:
        if (bits := netloc.split("@")) and len(bits) > 1:
            netloc = f"{bits[0]}@hidden"
        else:
            netloc = "hidden"

    if level > 2:
        return urlunparse([scheme, netloc, "", "", "", ""])

    return urlunparse([scheme, netloc, path, params, query, fragment])


def _sanitise_path(path: str) -> str:
    """Sanitise a file path by shortening it."""
    bits = list(reversed(Path(path).parts))
    result = [bits.pop(0)]
    for bit in bits:
        if RE1.match(bit) or RE2.match(bit):
            # keep earthkit-data folder patterns
            result.append(bit)
            continue
        if result[-1] == "...":
            continue
        result.append("...")
    result = os.path.join(*reversed(result))
    if bits[-1] == "/":
        result = os.path.join("/", result)

    return result
