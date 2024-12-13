# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json

from anemoi.utils.mars.requests import print_request

from . import Command


class Requests(Command):
    """Convert a JSON requests file to MARS format."""

    def add_arguments(self, command_parser):
        command_parser.add_argument("input")
        command_parser.add_argument("output")
        command_parser.add_argument("--verb", default="retrieve")
        command_parser.add_argument("--only-one-field", action="store_true")

    def run(self, args):
        with open(args.input) as f:
            requests = json.load(f)

        if args.only_one_field:
            for r in requests:
                for key in (
                    "grid",
                    "area",
                ):
                    r.pop(key, None)
                for k, v in list(r.items()):
                    if isinstance(v, list):
                        r[k] = v[-1]

        with open(args.output, "w") as f:
            for r in requests:
                print_request(args.verb, r, file=f)


command = Requests
