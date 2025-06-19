# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import shutil

from argparse import ArgumentParser
from argparse import Namespace
from argparse import BooleanOptionalAction

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
            "--source",
            type=str,
            required=True,
            help="Path to the checkpoint file containing the metadata."
        )
        command_parser.add_argument(
            "--target",
            type=str,
            help="Path to checkpoint without metadata. Required unless --inplace is set."
        )
        command_parser.add_argument(
            "--inplace",
            action=BooleanOptionalAction,
            help="If set, update the source file in place instead of writing to a separate target."
        )

    def run(self, args: Namespace) -> None:
        """Execute the command with the provided arguments.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        if not args.inplace and not args.target:
            raise ValueError("Argument --target is required unless --inplace is set")
            
        if args.inplace:
            target = args.source
        else:    
            shutil.copy2(args.source, args.target)
            target = args.target

        remove_metadata(target)


command = RemoveMetadata
