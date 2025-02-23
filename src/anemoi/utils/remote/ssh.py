# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
import os
import random
import shlex
import subprocess

from ..humanize import bytes_to_human
from . import BaseUpload

LOGGER = logging.getLogger(__name__)


def call_process(*args: str) -> str:
    """Execute a subprocess with the given arguments and return its output.

    Parameters
    ----------
    args : str
        The command and its arguments to execute.

    Returns
    -------
    str
        The standard output of the command.

    Raises
    ------
    RuntimeError
        If the command returns a non-zero exit code.
    """
    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        print(stdout)
        msg = f"{' '.join(args)} failed: {stderr}"
        raise RuntimeError(msg)

    return stdout.decode("utf-8").strip()


class SshBaseUpload(BaseUpload):

    def _parse_target(self, target: str) -> tuple[str, str]:
        """Parse the SSH target string into hostname and path.

        Parameters
        ----------
        target : str
            The SSH target string in the format 'ssh://hostname:path'.

        Returns
        -------
        tuple[str, str]
            A tuple containing the hostname and the path.

        Raises
        ------
        Exception
            If the path contains suspicious '..'.
        """
        assert target.startswith("ssh://"), target

        target = target[6:]
        hostname, path = target.split(":")

        if "+" in hostname:
            hostnames = hostname.split("+")
            hostname = hostnames[random.randint(0, len(hostnames) - 1)]

        if ".." in path.split("/"):
            raise Exception("Path contains suspicious '..' : {target}")

        return hostname, path

    def get_temporary_target(self, target: str, pattern: str) -> str:
        """Get a temporary target path based on the given pattern.

        Parameters
        ----------
        target : str
            The original target path.
        pattern : str
            The pattern to format the temporary path.

        Returns
        -------
        str
            The temporary target path.
        """
        hostname, path = self._parse_target(target)
        if pattern is not None:
            dirname, basename = os.path.split(path)
            path = pattern.format(dirname=dirname, basename=basename)
        return f"ssh://{hostname}:{path}"

    def rename_target(self, target: str, new_target: str) -> None:
        """Rename the target to a new target path.

        Parameters
        ----------
        target : str
            The original target path.
        new_target : str
            The new target path.
        """
        hostname, path = self._parse_target(target)
        hostname, new_path = self._parse_target(new_target)
        call_process("ssh", hostname, "mkdir", "-p", shlex.quote(os.path.dirname(new_path)))
        call_process("ssh", hostname, "mv", shlex.quote(path), shlex.quote(new_path))

    def delete_target(self, target: str) -> None:
        """Delete the target path.

        Parameters
        ----------
        target : str
            The target path to delete.
        """
        pass
        # hostname, path = self._parse_target(target)
        # LOGGER.info(f"Deleting {target}")
        # call_process("ssh", hostname, "rm", "-rf", shlex.quote(path))


class RsyncUpload(SshBaseUpload):

    def _transfer_file(
        self, source: str, target: str, overwrite: bool, resume: bool, verbosity: int, threads: int, config: dict = None
    ) -> int:
        """Transfer a file using rsync.

        Parameters
        ----------
        source : str
            The source file path.
        target : str
            The target file path.
        overwrite : bool
            Whether to overwrite the target if it exists.
        resume : bool
            Whether to resume the transfer if possible.
        verbosity : int
            The verbosity level.
        threads : int
            The number of threads to use.
        config : dict, optional
            Additional configuration options.

        Returns
        -------
        int
            The size of the transferred file.
        """
        hostname, path = self._parse_target(target)

        size = os.path.getsize(source)

        if verbosity > 0:
            LOGGER.info(f"{self.action} {source} to {target} ({bytes_to_human(size)})")

        call_process("ssh", hostname, "mkdir", "-p", shlex.quote(os.path.dirname(path)))
        call_process(
            "rsync",
            "-av",
            "--partial",
            # it would be nice to avoid two ssh calls, but the following is not possible,
            # this is because it requires a shell command and would not be safe.
            # # f"--rsync-path='mkdir -p {os.path.dirname(path)} && rsync'",
            source,
            f"{hostname}:{path}",
        )
        return size


class ScpUpload(SshBaseUpload):

    def _transfer_file(
        self, source: str, target: str, overwrite: bool, resume: bool, verbosity: int, threads: int, config: dict = None
    ) -> int:
        """Transfer a file using scp.

        Parameters
        ----------
        source : str
            The source file path.
        target : str
            The target file path.
        overwrite : bool
            Whether to overwrite the target if it exists.
        resume : bool
            Whether to resume the transfer if possible.
        verbosity : int
            The verbosity level.
        threads : int
            The number of threads to use.
        config : dict, optional
            Additional configuration options.

        Returns
        -------
        int
            The size of the transferred file.

        Raises
        ------
        ValueError
            If the target already exists and overwrite or resume is not specified.
        """
        hostname, path = self._parse_target(target)

        size = os.path.getsize(source)

        if verbosity > 0:
            LOGGER.info(f"{self.action} {source} to {target} ({bytes_to_human(size)})")

        remote_size = None
        try:
            out = call_process("ssh", hostname, "stat", "-c", "%s", shlex.quote(path))
            remote_size = int(out)
        except RuntimeError:
            remote_size = None

        if remote_size is not None:
            if remote_size != size:
                LOGGER.warning(
                    f"{target} already exists, but with different size, re-uploading (remote={remote_size}, local={size})"
                )
            elif resume:
                # LOGGER.info(f"{target} already exists, skipping")
                return size

        if remote_size is not None and not overwrite and not resume:
            raise ValueError(f"{target} already exists, use 'overwrite' to replace or 'resume' to skip")

        call_process("ssh", hostname, "mkdir", "-p", shlex.quote(os.path.dirname(path)))
        call_process("scp", source, shlex.quote(f"{hostname}:{path}"))

        return size


def upload(source: str, target: str, **kwargs) -> None:
    """Upload a file or folder to the target location using rsync.

    Parameters
    ----------
    source : str
        The source file or folder path.
    target : str
        The target path.
    kwargs : dict
        Additional arguments for the transfer.
    """
    uploader = RsyncUpload()

    if os.path.isdir(source):
        uploader.transfer_folder(source=source, target=target, **kwargs)
    else:
        uploader.transfer_file(source=source, target=target, **kwargs)
