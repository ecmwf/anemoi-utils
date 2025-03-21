# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import argparse
import importlib
import logging
import os
import sys
import traceback
from typing import Callable

try:
    import argcomplete
except ImportError:
    argcomplete = None

LOG = logging.getLogger(__name__)


class Command:
    """Base class for commands."""

    accept_unknown_args = False

    def run(self, args: argparse.Namespace) -> None:
        """Run the command.

        Parameters
        ----------
        args : argparse.Namespace
            The arguments for the command
        """
        raise NotImplementedError(f"Command not implemented: {args.command}")


def make_parser(description: str, commands: dict[str, Command]) -> argparse.ArgumentParser:
    """Create an argument parser for the CLI.

    Parameters
    ----------
    description : str
        The description of the CLI
    commands : dict[str, Command]
        A dictionary of command names to Command instances

    Returns
    -------
    argparse.ArgumentParser
        The argument parser
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        "-V",
        action="store_true",
        help="show the version and exit",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Debug mode",
    )

    subparsers = parser.add_subparsers(help="commands:", dest="command")
    for name, command in commands.items():
        command_parser = subparsers.add_parser(name, description=command.__doc__, help=command.__doc__)
        command.add_arguments(command_parser)

    return parser


class Failed(Command):
    """Command not available."""

    def __init__(self, name: str, error: ImportError):
        """Initialize the Failed command.

        Parameters
        ----------
        name : str
            The name of the command
        error : ImportError
            The error that occurred
        """
        self.name = name
        self.error = error
        traceback.print_tb(error.__traceback__)

    def add_arguments(self, command_parser: argparse.ArgumentParser) -> None:
        """Add arguments to the command parser.

        Parameters
        ----------
        command_parser : argparse.ArgumentParser
            The command parser
        """
        command_parser.add_argument("x", nargs=argparse.REMAINDER)

    def run(self, args: argparse.Namespace) -> None:
        """Run the command.

        Parameters
        ----------
        args : argparse.Namespace
            The arguments for the command
        """
        print(f"Command '{self.name}' not available: {self.error}")
        sys.exit(1)


def register_commands(here: str, package: str, select: Callable, fail: Callable = None) -> dict[str, Command]:
    """Register commands from a package.

    Parameters
    ----------
    here : str
        The directory containing the commands
    package : str
        The package name
    select : Callable
        A function to select the command object from the module
    fail : Callable, optional
        A function to create a Failed command if a command cannot be imported

    Returns
    -------
    dict[str, Command]
        A dictionary of command names to Command instances
    """
    result = {}
    not_available = {}

    for p in sorted(os.listdir(here)):
        full = os.path.join(here, p)
        if p.startswith("_"):
            continue
        if not (p.endswith(".py") or (os.path.isdir(full) and os.path.exists(os.path.join(full, "__init__.py")))):
            continue

        name, _ = os.path.splitext(p)

        try:
            imported = importlib.import_module(
                f".{name}",
                package=package,
            )
        except ImportError as e:
            not_available[name] = e
            continue

        obj = select(imported)
        if obj is None:
            continue

        if hasattr(obj, "command"):
            name = obj.command

        if name in result:
            msg = f"Duplicate command '{name}', please choose a different command name for {type(obj)}"
            raise ValueError(msg)
        if " " in name:
            msg = f"Commands cannot contain spaces: '{name}' in {type(obj)}"
            raise ValueError(msg)

        result[name] = obj

    for name, e in not_available.items():
        if fail is None:
            pass
        if callable(fail):
            result[name] = fail(name, e)

    return result


def cli_main(version: str, description: str, commands: dict[str, Command]) -> None:
    """Main entry point for the CLI.

    Parameters
    ----------
    version : str
        The version of the CLI
    description : str
        The description of the CLI
    commands : dict[str, Command]
        A dictionary of command names to Command instances
    """
    parser = make_parser(description, commands)
    args, unknown = parser.parse_known_args()
    if argcomplete:
        argcomplete.autocomplete(parser)

    if args.version:
        print(version)
        return

    if args.command is None:
        parser.print_help()
        return

    cmd = commands[args.command]

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG if args.debug else logging.INFO,
    )

    if unknown and not cmd.accept_unknown_args:
        # This should trigger an error
        parser.parse_args()

    try:
        if unknown:
            cmd.run(args, unknown)
        else:
            cmd.run(args)
    except ValueError as e:
        traceback.print_exc()
        LOG.error("\n💣 %s", str(e).lstrip())
        LOG.error("💣 Exiting")
        sys.exit(1)

    sys.exit(0)
