# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import json
import logging
import os
from argparse import ArgumentParser
from argparse import Namespace

from anemoi.utils.checkpoints import add_embedded_files
from anemoi.utils.checkpoints import list_embedded_files
from anemoi.utils.checkpoints import remove_embedded_files

from . import Command

LOG = logging.getLogger(__name__)


class EmbeddedFiles(Command):
    """Manage embedded files from a checkpoint file."""

    def add_arguments(self, command_parser: ArgumentParser) -> None:
        """Add command line arguments to the parser.

        Parameters
        ----------
        command_parser : ArgumentParser
            The argument parser to which the arguments will be added.
        """

        command_parser.add_argument("path", help="Path to the checkpoint.")

        group = command_parser.add_mutually_exclusive_group(required=True)

        group.add_argument(
            "--list",
            action="store_true",
            help=("List the embedded files in the checkpoint and print them to the standard output"),
        )
        group.add_argument(
            "--add",
            action="store_true",
            help=("Add files to the embedded files in the checkpoint from the content"),
        )

        group.add_argument(
            "--remove",
            action="store_true",
            help=("Remove files from the embedded files in the checkpoint."),
        )
        group.add_argument(
            "--extract",
            action="store_true",
            help=("Extract files from the embedded files in the checkpoint."),
        )

        command_parser.add_argument(
            "--file",
            nargs="+",
            required=False,
            help="File(s) to add, remove, or extract.",
        )

        command_parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing embedded files with the same name when adding new files.",
        )

    def _validate_args(self, args: Namespace) -> None:
        """Validate command line arguments.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.

        Raises
        ------
        ValueError
            If required arguments are missing.
        """
        if args.add and not args.file:
            raise ValueError("--file is required when using --add")

    def run(self, args: Namespace) -> None:
        """Execute the command based on the provided arguments.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        self._validate_args(args)

        if args.list:
            return self.list(args)

        if args.add:
            return self.add(args)

        if args.remove:
            return self.remove(args)

        if args.extract:
            return self.extract(args)

    def list(self, args: Namespace) -> None:
        """List the embedded files in the checkpoint.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        for name, size, date in list_embedded_files(args.path):
            print(name, json.dumps({"size": size, "modified_time": date}, indent=2, default=str))

    def add(self, args: Namespace) -> None:
        """Add files to the embedded files in the checkpoint from the content.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        LOG.info("Adding files to the embedded files in the checkpoint.")

        file_paths = {}
        for file in args.file:
            name = os.path.basename(file)
            LOG.info(f"Adding file: {file} as {name}")
            file_paths[name] = file

        add_embedded_files(args.path, file_paths, args.overwrite)

    def remove(self, args: Namespace) -> None:
        """Remove files from the embedded files in the checkpoint.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        remove_embedded_files(args.path, set(args.file))

    def extract(self, args: Namespace) -> None:
        """Remove files from the embedded files in the checkpoint.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        pass


command = EmbeddedFiles
