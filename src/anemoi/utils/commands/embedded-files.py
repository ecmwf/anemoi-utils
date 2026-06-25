# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging
import os
from argparse import ArgumentParser
from argparse import Namespace

from anemoi.utils.checkpoints import add_embedded_files
from anemoi.utils.checkpoints import extract_embedded_files
from anemoi.utils.checkpoints import extract_from_checkpoint
from anemoi.utils.checkpoints import list_embedded_files
from anemoi.utils.checkpoints import remove_embedded_files

from . import Command

LOG = logging.getLogger(__name__)


class EmbeddedFiles(Command):
    """Manage embedded files from a checkpoint file.

    The command line interface follows the conventions of common archive tools
    such as ``tar``, ``zip`` and ``unzip``: an action verb, followed by the
    archive (the checkpoint), followed by the file names to operate on.

    Examples
    --------
    List all embedded files in a checkpoint::

        anemoi-utils embedded-files list my-checkpoint.ckpt

    List them in a long format, showing the size and modification time::

        anemoi-utils embedded-files list my-checkpoint.ckpt -l

    Add one or more files to a checkpoint (the file's base name is used as the
    embedded name)::

        anemoi-utils embedded-files add my-checkpoint.ckpt config.yaml notes.txt

    Recursively add the contents of a directory (symlinks are followed)::

        anemoi-utils embedded-files add my-checkpoint.ckpt -r my-directory

    Overwrite an embedded file that already exists::

        anemoi-utils embedded-files add my-checkpoint.ckpt config.yaml --overwrite

    Remove embedded files by name::

        anemoi-utils embedded-files remove my-checkpoint.ckpt notes.txt config.yaml

    Extract embedded files to the current directory, or to a chosen one::

        anemoi-utils embedded-files extract my-checkpoint.ckpt config.yaml
        anemoi-utils embedded-files extract my-checkpoint.ckpt config.yaml \\
            --directory ./extracted --overwrite

    Print an embedded file to the standard output (resolves the
    ``checkpoint://`` scheme)::

        anemoi-utils embedded-files cat my-checkpoint.ckpt checkpoint://config.yaml
    """

    def add_arguments(self, command_parser: ArgumentParser) -> None:
        """Add command line arguments to the parser.

        The interface follows the conventions of common archive tools such as
        ``tar``, ``zip`` and ``unzip``: an action verb, followed by the archive
        (the checkpoint), followed by the file names to operate on.

        Parameters
        ----------
        command_parser : ArgumentParser
            The argument parser to which the arguments will be added.
        """

        actions = command_parser.add_subparsers(dest="action", required=True, metavar="action")

        list_parser = actions.add_parser("list", help="List the embedded files in the checkpoint.")
        list_parser.add_argument("checkpoint", help="Path to the checkpoint.")
        list_parser.add_argument(
            "-l",
            "--long",
            action="store_true",
            help="Use a long listing format, showing the size and modification time of each file.",
        )

        add_parser = actions.add_parser("add", help="Add files to the checkpoint.")
        add_parser.add_argument("checkpoint", help="Path to the checkpoint.")
        add_parser.add_argument("file", nargs="+", help="File(s) or directory(ies) to add.")
        add_parser.add_argument(
            "-r",
            "--recursive",
            action="store_true",
            help="Recursively add the contents of directories.",
        )
        add_parser.add_argument(
            "-o",
            "--overwrite",
            action="store_true",
            help="Overwrite existing embedded files with the same name.",
        )

        remove_parser = actions.add_parser("remove", help="Remove files from the checkpoint.")
        remove_parser.add_argument("checkpoint", help="Path to the checkpoint.")
        remove_parser.add_argument("file", nargs="+", help="File(s) to remove.")

        extract_parser = actions.add_parser("extract", help="Extract files from the checkpoint.")
        extract_parser.add_argument("checkpoint", help="Path to the checkpoint.")
        extract_parser.add_argument("file", nargs="+", help="File(s) to extract.")
        extract_parser.add_argument(
            "-C",
            "--directory",
            help="Extract files into this directory (default: current directory).",
        )
        extract_parser.add_argument(
            "-f",
            "--overwrite",
            action="store_true",
            help="Overwrite existing files when extracting.",
        )

        cat_parser = actions.add_parser("cat", help="Print an embedded file to the standard output.")
        cat_parser.add_argument("checkpoint", help="Path to the checkpoint.")
        cat_parser.add_argument("name", help="Name of the embedded file (for testing the checkpoint:// scheme).")

    def run(self, args: Namespace) -> None:
        """Execute the command based on the provided arguments.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        return getattr(self, args.action)(args)

    def list(self, args: Namespace) -> None:
        """List the embedded files in the checkpoint.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        files = list_embedded_files(args.checkpoint)

        if not args.long:
            for name, _, _ in files:
                print(name)
            return

        for name, size, date in files:
            print(f"{size:>12}  {date:%Y-%m-%d %H:%M:%S}  {name}")

    def add(self, args: Namespace) -> None:
        """Add files to the embedded files in the checkpoint from the content.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        LOG.info("Adding files to the embedded files in the checkpoint.")

        checkpoint_realpath = os.path.realpath(args.checkpoint)
        file_paths = {}

        def add_one(name: str, file: str) -> None:
            if os.path.realpath(file) == checkpoint_realpath:
                raise ValueError(f"Cannot add the checkpoint file itself as an embedded file: {file}")
            LOG.info(f"Adding file: {file} as {name}")
            file_paths[name] = file

        for file in args.file:

            if os.path.isdir(file):
                if not args.recursive:
                    raise ValueError(f"{file} is a directory, use -r/--recursive to add directories.")

                top = os.path.basename(os.path.normpath(file))
                # followlinks=True so that symlinked directories are followed
                for root, _, files in os.walk(file, followlinks=True):
                    for filename in files:
                        full = os.path.join(root, filename)
                        # Build the embedded name using forward slashes (zip convention)
                        relative = os.path.relpath(full, file)
                        name = "/".join([top, *relative.split(os.sep)])
                        add_one(name, full)
                continue

            add_one(os.path.basename(file), file)

        add_embedded_files(args.checkpoint, file_paths, args.overwrite)

    def remove(self, args: Namespace) -> None:
        """Remove files from the embedded files in the checkpoint.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        remove_embedded_files(args.checkpoint, set(args.file))

    def extract(self, args: Namespace) -> None:
        """Extract files from the embedded files in the checkpoint.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        extract_embedded_files(
            args.checkpoint, set(args.file), target_directory=args.directory, overwrite=args.overwrite
        )

    def cat(self, args: Namespace) -> None:
        """For testing checkpoint:// scheme."""
        local_path = extract_from_checkpoint(args.checkpoint, args.name)
        with open(local_path, "rb") as f:
            data = f.read()
            print(data.decode("utf-8"))


command = EmbeddedFiles
