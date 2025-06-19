# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from argparse import ArgumentParser
from argparse import Namespace
import shutil

from anemoi.utils.checkpoints import remove_metadata

from . import Command


class RemoveMetadata(Command):
    """Delete the metadata from a checkpoint and create a new checkpoint with the metadata removed."""

    def add_arguments(self, command_parser: ArgumentParser) -> None:
        """Add arguments to the command parser.

        Parameters
        ----------
        command_parser : ArgumentParser
            The argument parser to which the arguments will be added.
        """
        command_parser.add_argument(
            "--input", help="A path to the checkpoint file containing the metadata."
        )

        command_parser.add_argument(
            "--output", help="Path to checkpoint without metadata"
        )
    
    def run(self, args: Namespace) -> None:
        """Execute the command with the provided arguments.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        shutil.copy2(args.input, args.output)
        remove_metadata(args.output)


command = RemoveMetadata
