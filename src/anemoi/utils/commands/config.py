# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from argparse import ArgumentParser
from argparse import Namespace

from ..settings import ANEMOI_SETTINGS_FILE_LOCATION
from ..settings import SETTINGS
from . import Command


class Config(Command):
    """Handle configuration related commands."""

    def add_arguments(self, command_parser: ArgumentParser) -> None:
        """Add arguments to the command parser.

        Parameters
        ----------
        command_parser : ArgumentParser
            The argument parser to which the arguments will be added.
        """
        command_parser.add_argument("--path", help="Print path to config file")

    def run(self, args: Namespace) -> None:
        """Execute the command with the provided arguments.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """

        if args.path:
            print(ANEMOI_SETTINGS_FILE_LOCATION)
        else:
            print(SETTINGS.model_dump_json(indent=4))


command = Config
