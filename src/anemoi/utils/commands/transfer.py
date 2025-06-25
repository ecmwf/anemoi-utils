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

from anemoi.utils.remote import transfer

from . import Command


class Transfer(Command):
    """Transfer files or folders from the source to the target location."""

    def add_arguments(self, command_parser: ArgumentParser) -> None:
        """Add arguments to the command parser.

        Parameters
        ----------
        command_parser : ArgumentParser
            The argument parser to which the arguments will be added.
        """
        command_parser.add_argument(
            "--source", help="A path to a local file or folder or a URL to a file or a folder on S3."
        )
        command_parser.add_argument(
            "--target", help="A path to a local file or folder or a URL to a file or a folder on S3 or a remote folder."
        )
        command_parser.add_argument(
            "--overwrite",
            action="store_true",
            help="If the data is already on in the target location it will be overwritten..",
        )
        command_parser.add_argument(
            "--resume",
            action="store_true",
            help="If the data is already on S3 it will not be uploaded, unless the remote file has a different size.",
        )
        command_parser.add_argument("--verbosity", default=1, help="The level of verbosity, by default 1.")
        command_parser.add_argument(
            "--progress", default=None, help="A callable that will be called with the number of files."
        )
        command_parser.add_argument(
            "--threads", default=1, help="The number of threads to use when uploading a directory, by default 1."
        )

    def run(self, args: Namespace) -> None:
        """Execute the command with the provided arguments.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        transfer(
            source=args.source,
            target=args.target,
            overwrite=args.overwrite,
            resume=args.resume,
            verbosity=args.verbosity,
            progress=args.progress,
            threads=args.threads,
            temporary_target=False,
        )


command = Transfer
