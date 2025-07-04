# (C) Copyright 2024 Anemoi contributors.
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
import shutil
import subprocess
from argparse import ArgumentParser
from argparse import Namespace
from tempfile import TemporaryDirectory
from typing import Any
from typing import Dict

import yaml

from . import Command

LOG = logging.getLogger(__name__)

EDITOR_OPTIONS = {"code": ["--wait"]}


class Metadata(Command):
    """Edit, remove, dump or load metadata from a checkpoint file."""

    def add_arguments(self, command_parser: ArgumentParser) -> None:
        """Add command line arguments to the parser.

        Parameters
        ----------
        command_parser : ArgumentParser
            The argument parser to which the arguments will be added.
        """
        from anemoi.utils.checkpoints import DEFAULT_NAME

        command_parser.add_argument("path", help="Path to the checkpoint.")

        group = command_parser.add_mutually_exclusive_group(required=True)

        group.add_argument(
            "--dump",
            action="store_true",
            help=(
                "Extract the metadata from the checkpoint and print it to the standard output"
                " or the file specified by ``--output``, in JSON or YAML format."
            ),
        )
        group.add_argument(
            "--load",
            action="store_true",
            help=(
                "Set the metadata in the checkpoint from the content"
                " of a file specified by the ``--input`` argument."
            ),
        )

        group.add_argument(
            "--edit",
            action="store_true",
            help=(
                "Edit the metadata in place, using the specified editor."
                " See the ``--editor`` argument for more information."
            ),
        )

        group.add_argument(
            "--view",
            action="store_true",
            help=(
                "View the metadata in place, using the specified pager."
                " See the ``--pager`` argument for more information."
            ),
        )

        group.add_argument(
            "--remove",
            action="store_true",
            help="Remove the metadata from the checkpoint.",
        )

        group.add_argument(
            "--supporting-arrays",
            action="store_true",
            help="Print the supporting arrays.",
        )

        group.add_argument(
            "--get",
            help="Navigate the metadata via dot-separated path.",
        )

        group.add_argument(
            "--pytest",
            action="store_true",
            help=("Extract the metadata from the checkpoint so it can be added to the test suite."),
        )

        command_parser.add_argument(
            "--name",
            default=DEFAULT_NAME,
            help="Name of metadata record to be used with the actions above.",
        )

        command_parser.add_argument(
            "--input",
            help="The output file name to be used by the ``--load`` option.",
        )

        command_parser.add_argument(
            "--output",
            help="The output file name to be used by the ``--dump`` option.",
        )

        command_parser.add_argument(
            "--inplace",
            action="store_true",
            help="If set, update the source file in place instead of writing to a separate target.",
        )

        command_parser.add_argument(
            "--editor",
            help="Editor to use for the ``--edit`` option. Default to ``$EDITOR`` if defined, else ``vi``.",
            default=os.environ.get("EDITOR", "vi"),
        )

        command_parser.add_argument(
            "--pager",
            help="Editor to use for the ``--view`` option. Default to ``$PAGER`` if defined, else ``less``.",
            default=os.environ.get("PAGER", "less"),
        )

        command_parser.add_argument(
            "--json",
            action="store_true",
            help="Use the JSON format with ``--dump``, ``--view`` and ``--edit``.",
        )

        command_parser.add_argument(
            "--yaml",
            action="store_true",
            help="Use the YAML format with ``--dump``, ``--view`` and ``--edit``.",
        )

    def run(self, args: Namespace) -> None:
        """Execute the command based on the provided arguments.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        if args.edit:
            return self.edit(args)

        if args.view:
            return self.view(args)

        if args.get:
            return self.get(args)

        if args.remove:
            return self.remove(args)

        if args.dump or args.pytest:
            return self.dump(args)

        if args.load:
            return self.load(args)

        if args.supporting_arrays:
            return self.supporting_arrays(args)

    def edit(self, args: Namespace) -> None:
        """Edit the metadata in place using the specified editor.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        return self._edit(args, view=False, cmd=args.editor)

    def view(self, args: Namespace) -> None:
        """View the metadata in place using the specified pager.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        return self._edit(args, view=True, cmd=args.pager)

    def _edit(self, args: Namespace, view: bool, cmd: str) -> None:
        """Internal method to edit or view the metadata.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        view : bool
            If True, view the metadata; otherwise, edit it.
        cmd : str
            The command to use for editing or viewing.
        """
        from anemoi.utils.checkpoints import load_metadata
        from anemoi.utils.checkpoints import replace_metadata

        kwargs: Dict[str, Any] = {}

        if args.json:
            ext = "json"
            dump = json.dump
            load = json.load
            if args.test:
                kwargs = {"sort_keys": True}
            else:
                kwargs = {"indent": 4, "sort_keys": True}
        else:
            ext = "yaml"
            dump = yaml.dump
            load = yaml.safe_load
            kwargs = {"default_flow_style": False}

        with TemporaryDirectory() as temp_dir:

            path = os.path.join(temp_dir, f"checkpoint.{ext}")
            metadata = load_metadata(args.path)

            with open(path, "w") as f:
                dump(metadata, f, **kwargs)

            subprocess.check_call([cmd, *EDITOR_OPTIONS.get(cmd, []), path])

            if not view:
                with open(path) as f:
                    edited = load(f)

                if edited != metadata:
                    replace_metadata(args.path, edited)
                else:
                    LOG.info("No changes made.")

    def remove(self, args: Namespace) -> None:
        """Remove the metadata from the checkpoint.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        from anemoi.utils.checkpoints import remove_metadata

        if args.inplace and args.output:
            raise ValueError("Only choose one of --inplace and --output")

        LOG.info("Removing metadata from %s", args.path)

        if args.inplace:
            output = args.path
        else:
            if not args.output:
                raise ValueError("Argument --output is required unless --inplace is set")

            shutil.copy2(args.path, args.output)
            output = args.output

        LOG.info("Writing checkpoint at %s", output)
        remove_metadata(output)

    def dump(self, args: Namespace) -> None:
        """Dump the metadata from the checkpoint to a file or standard output.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        from anemoi.utils.checkpoints import load_metadata

        if args.output:
            file = open(args.output, "w")
        else:
            file = None

        metadata = load_metadata(args.path)
        if args.pytest:
            from anemoi.inference.testing.mock_checkpoint import minimum_mock_checkpoint

            # We remove all unessential metadata for testing purposes
            metadata = minimum_mock_checkpoint(metadata)

        if args.yaml:
            print(yaml.dump(metadata, indent=2, sort_keys=True), file=file)
            return

        if args.json or True:
            if args.pytest:
                print(json.dumps(metadata, sort_keys=True), file=file)
            else:
                print(json.dumps(metadata, indent=4, sort_keys=True), file=file)
            return

    def get(self, args: Namespace) -> None:
        """Navigate and print the metadata via a dot-separated path.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        from pprint import pprint

        from anemoi.utils.checkpoints import load_metadata

        metadata = load_metadata(args.path, name=args.name)

        if args.get == ".":
            print("Metadata from root: ", list(metadata.keys()))
            return

        for key in args.get.split("."):
            if key == "":
                keys = list(metadata.keys())
                print(f"Metadata keys from {args.get[:-1]}: ", keys)
                return
            else:
                metadata = metadata[key]

        print(f"Metadata values for {args.get}: ", end="\n" if isinstance(metadata, (dict, list)) else "")
        if isinstance(metadata, dict):
            pprint(metadata, indent=2, compact=True)
        else:
            print(metadata)

    def load(self, args: Namespace) -> None:
        """Load metadata into the checkpoint from a specified file.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        from anemoi.utils.checkpoints import has_metadata
        from anemoi.utils.checkpoints import replace_metadata
        from anemoi.utils.checkpoints import save_metadata

        if args.input is None:
            raise ValueError("Please specify a value for --input")

        _, ext = os.path.splitext(args.input)
        if ext == ".json" or args.json:
            with open(args.input) as f:
                metadata = json.load(f)

        elif ext in (".yaml", ".yml") or args.yaml:
            with open(args.input) as f:
                metadata = yaml.safe_load(f)

        else:
            raise ValueError(f"Unknown file extension {ext}. Please specify --json or --yaml")

        if has_metadata(args.path, name=args.name):
            replace_metadata(args.path, metadata)
        else:
            save_metadata(args.path, metadata, name=args.name)

    def supporting_arrays(self, args: Namespace) -> None:
        """Print the supporting arrays from the metadata.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        from anemoi.utils.checkpoints import load_metadata

        _, supporting_arrays = load_metadata(args.path, supporting_arrays=True)

        for name, array in supporting_arrays.items():
            print(f"{name}: shape={array.shape} dtype={array.dtype}")


command = Metadata
