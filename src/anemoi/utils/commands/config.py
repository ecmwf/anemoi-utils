# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import json

from ..config import config_path
from ..config import load_config
from . import Command


class Config(Command):

    def add_arguments(self, command_parser):
        command_parser.add_argument("--path", help="Print path to config file")

    def run(self, args):
        if args.path:
            print(config_path())
        else:
            print(json.dumps(load_config(), indent=4))


command = Config
