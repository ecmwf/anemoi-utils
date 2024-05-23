#!/usr/bin/env python
# (C) Copyright 2024 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#


import json

from . import Command


class Checkpoint(Command):

    def add_arguments(self, command_parser):
        command_parser.add_argument("path", help="Path to the checkpoint.")

    def run(self, args):
        from anemoi.utils.checkpoints import load_metadata

        checkpoint = load_metadata(args.path, "*.json")
        print(json.dumps(checkpoint, sort_keys=True, indent=4))


command = Checkpoint
