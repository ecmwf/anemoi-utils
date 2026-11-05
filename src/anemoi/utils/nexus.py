# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Build an asset's record for Anemoi Nexus.

Each package that owns an asset format (``anemoi-datasets`` for datasets,
``anemoi-inference`` for checkpoints) has a ``nexus-record`` command that reads
the asset and prints its Nexus record, which ``nexus-client create <kind>
<key> --file record.json`` then sends as is. ``nexus-client`` never reads an
asset's format itself.

A record is a JSON object: the asset's identity (``uuid``, ``name``), its
``metadata``, plus the attributes Nexus needs to file it. The attributes come
from the command line (``--owner``, ``--project``/``--projects``,
``--license``/``--licenses``) or from an ``@FILE`` (JSON or YAML), in which
``project``/``projects`` and ``license``/``licenses`` (or ``licence``/
``licences``) may be singular or plural; the command line wins over the file.
"""

from __future__ import annotations

import json
import os
import sys
from argparse import ArgumentParser
from argparse import Namespace
from typing import Any

import yaml

#: Keys of an ``@FILE`` that hold a list, by their singular and plural spellings.
LIST_KEYS = {
    "project": "projects",
    "projects": "projects",
    "license": "licenses",
    "licenses": "licenses",
    "licence": "licenses",
    "licences": "licenses",
}


def _as_list(value: Any, key: str) -> list[str]:
    """A list of names from a name, a comma-separated string or a list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value):
        return [v.strip() for v in value if v.strip()]
    raise ValueError(f"{key!r} must be a name or a list of names, not {value!r}")


def normalise_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """The record attributes of *attributes*: ``project``/``projects`` become
    ``projects`` and ``license``/``licenses``/``licence``/``licences`` become
    ``licenses`` (always lists); every other key is kept as it is.
    """
    out: dict[str, Any] = {}
    for key, value in attributes.items():
        target = LIST_KEYS.get(key)
        if target is None:
            out[key] = value
            continue
        if target in out:
            raise ValueError(f"both {key!r} and another spelling of {target!r} are given")
        out[target] = _as_list(value, key)
    return out


def load_attributes(path: str) -> dict[str, Any]:
    """The record attributes in the JSON or YAML file *path* (a leading ``@``
    is dropped), normalised by :func:`normalise_attributes`.
    """
    if path.startswith("@"):
        path = path[1:]
    with open(path) as f:
        # YAML is a superset of JSON: one loader reads both.
        data = yaml.safe_load(f)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: the attributes must be a JSON/YAML object")
    return normalise_attributes(data)


def add_nexus_record_arguments(parser: ArgumentParser) -> None:
    """Add the record-attribute arguments shared by every ``nexus-record``
    command: ``@FILE``, ``--name``, ``--owner``, ``--project(s)``,
    ``--license(s)`` and ``--output``.
    """
    parser.add_argument(
        "attributes",
        nargs="?",
        metavar="@FILE",
        help="A JSON or YAML file of record attributes (owner, project(s), license(s), ...);"
        " the options below win over it.",
    )
    parser.add_argument("--name", help="The asset's name in Nexus (default: from the asset).")
    parser.add_argument(
        "--owner",
        help="The asset's owner (honoured by Nexus for an admin or a service account).",
    )
    for singular, plural, what in (
        ("project", "projects", "Nexus projects"),
        ("license", "licenses", "licences"),
    ):
        parser.add_argument(
            f"--{plural}",
            action="append",
            default=[],
            metavar="A,B",
            help=f"The asset's {what}: comma-separated, repeatable.",
        )
        parser.add_argument(
            f"--{singular}",
            dest=plural,
            action="append",
            metavar="A",
            help=f"One of the asset's {what} (repeatable).",
        )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Write the record to FILE (default: stdout).",
    )


def record_attributes(args: Namespace) -> dict[str, Any]:
    """The record attributes of the parsed *args*: the ``@FILE``, then the
    options (which win over it).
    """
    attributes: dict[str, Any] = {}
    if args.attributes:
        if not args.attributes.startswith("@"):
            raise ValueError(f"{args.attributes!r}: the attributes file is given as @FILE")
        attributes = load_attributes(args.attributes)
    if args.name:
        attributes["name"] = args.name
    if args.owner:
        attributes["owner"] = args.owner
    for key in ("projects", "licenses"):
        values = [v for value in getattr(args, key) or [] for v in _as_list(value, key)]
        if values:
            attributes[key] = values
    return attributes


def nexus_record(
    *,
    uuid: str | None,
    metadata: dict[str, Any],
    name: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """An asset's Nexus record: ``uuid``, ``name`` (when known), ``metadata``
    and the *attributes* (whose ``name`` wins over *name*).
    """
    record: dict[str, Any] = {}
    if uuid:
        record["uuid"] = uuid
    if name:
        record["name"] = name
    record["metadata"] = metadata
    for key, value in (attributes or {}).items():
        if key in ("uuid", "metadata"):
            raise ValueError(f"{key!r} comes from the asset, not from the attributes")
        record[key] = value
    return record


def write_nexus_record(record: dict[str, Any], output: str | None = None) -> None:
    """Write *record* as JSON to *output* (a file), or to stdout."""
    text = json.dumps(record, indent=2, sort_keys=True, default=str) + "\n"
    if output:
        tmp = f"{output}.tmp"
        with open(tmp, "w") as f:
            f.write(text)
        os.replace(tmp, output)
    else:
        sys.stdout.write(text)
