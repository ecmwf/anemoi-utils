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
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from . import Command


def _make_migration_name(name: str) -> str:
    name = name.replace("-", "_").replace(" ", "_")
    now = int(datetime.now().timestamp())
    return f"{now}_{name}.py"


class GenerateMigration(Command):
    """Migrate a checkpoint"""

    def add_arguments(self, command_parser: ArgumentParser) -> None:
        """Add arguments to the command parser.

        Parameters
        ----------
        command_parser : ArgumentParser
            The argument parser to which the arguments will be added.
        """
        command_parser.add_argument("name", help="Name of the migration")
        command_parser.add_argument("--path", help="Path to the migration folder")

    def run(self, args: Namespace) -> None:
        """Execute the command with the provided arguments.

        Parameters
        ----------
        args : Namespace
            The arguments passed to the command.
        """
        name = _make_migration_name(args.name)
        with open(Path(args.path) / name, "w") as f:
            f.write(
                dedent(
                    """
                    from anemoi.utils.ckpt_migration import CkptType


                    def migrate(ckpt: CkptType) -> CkptType:
                        # Migrate my checkpoint
                        return ckpt
                """
                ).strip()
            )


command = GenerateMigration
