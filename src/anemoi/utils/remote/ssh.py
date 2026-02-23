# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import concurrent.futures
import logging
import os
import random
import shlex
import subprocess
import tempfile

import tqdm

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
    LOGGER.info("Running command: %s", " ".join(args))
    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        if stdout:
            LOGGER.warning(stdout.decode("utf-8", errors="replace").strip())
        msg = f"{' '.join(args)} failed: {stderr}"
        raise RuntimeError(msg)

    return stdout.decode("utf-8").strip()


def run_process(*args: str) -> None:
    """Execute a subprocess, forwarding its output directly to the terminal.

    Parameters
    ----------
    args : str
        The command and its arguments to execute.

    Raises
    ------
    RuntimeError
        If the command returns a non-zero exit code.
    """
    proc = subprocess.run(args, check=False)
    if proc.returncode != 0:
        msg = f"{' '.join(args)} failed"
        raise RuntimeError(msg)


class SshBaseUpload(BaseUpload):
    _default_tool: str  # must be defined by subclasses

    def __init__(self, tool: str = None) -> None:
        tool = tool or self._default_tool
        self._tool = tool.split()

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

    def prepare_checkpoint(self, _source: str, target: str) -> dict:
        hostname, path = self._parse_target(target)
        try:
            LOGGER.info(f"Fetching remote file sizes from {hostname}:{path}")
            out = call_process(
                "ssh",
                hostname,
                "find",
                shlex.quote(path),
                "-type",
                "f",
                "-printf",
                shlex.quote(r"%p\t%s\n"),
            )
            remote_sizes = {}
            for line in out.splitlines():
                if "\t" in line:
                    abs_path, size_str = line.rsplit("\t", 1)
                    remote_sizes[abs_path] = int(size_str)
            LOGGER.info(f"Fetched {len(remote_sizes):,} remote file sizes from {hostname}:{path}")
            return {"remote_sizes": remote_sizes}
        except RuntimeError:
            return {}  # Target directory does not exist yet


class MscpUpload(SshBaseUpload):
    _default_tool = "mscp"

    def copy(self, source: str, target: str, *, threads: int = 1, **kwargs) -> None:
        """Copy a file or a folder from the source to the target location.

        Parameters
        ----------
        source : str
            The source location.
        target : str
            The target location.
        threads : int, optional
            Number of parallel streams passed to mscp via ``-n``. mscp is always
            invoked as a single process; there is no outer multi-process parallelism.
        kwargs : dict
            Forwarded to :meth:`transfer_file`.
        """
        checkpoint = self.prepare_checkpoint(source, target)
        # mscp handles the entire transfer (files or directories) in one process.
        # `threads` maps to mscp's own -n flag, not to outer process parallelism.
        self.transfer_file(source=source, target=target, checkpoint=checkpoint, threads=threads, **kwargs)

    def _transfer_file(
        self,
        source: str,
        target: str,
        overwrite: bool,
        resume: bool,
        verbosity: int,
        threads: int,
        checkpoint: dict = None,
    ) -> int:
        """Transfer a file using mscp.

        Parameters
        ----------
        source : str
            The source file path.
        target : str
            The target file path.
        overwrite : bool
            Whether to overwrite the target if it exists.
        resume : bool
            Whether to resume the transfer if possible. Not supported by mscp;
            passing ``True`` will raise a ``NotImplementedError``.
        verbosity : int
            The verbosity level.
        threads : int
            The number of threads to use.
        checkpoint : dict, optional
            Checkpoint information for the transfer.

        Returns
        -------
        int
            The size of the transferred file.

        Raises
        ------
        NotImplementedError
            If ``resume`` is ``True``, as mscp does not support resuming partial transfers.
        """
        if resume:
            raise NotImplementedError("mscp does not support resuming partial transfers")

        hostname, path = self._parse_target(target)

        size = os.path.getsize(source)

        if os.path.isfile(source):
            if checkpoint is None:
                checkpoint = self.prepare_checkpoint(source, target)
            remote_size = checkpoint.get("remote_sizes", {}).get(path)

            if remote_size is not None:
                if remote_size != size:
                    LOGGER.warning(
                        f"{target} already exists, but with different size, re-uploading (remote={remote_size}, local={size})"
                    )

            if remote_size is not None and not overwrite:
                raise ValueError(f"{target} already exists, use 'overwrite' to replace")

        # mscp automatically appends the source basename to the destination.
        # If the target path already ends with that basename, pass the parent
        # directory to mscp to avoid doubling it (e.g. foo.zarr/foo.zarr).
        _, src_basename = os.path.split(source)
        dest_path = os.path.dirname(path) if os.path.basename(path) == src_basename else path
        LOGGER.debug(f"Copying {source} to {hostname}:{dest_path} with mscp")

        if verbosity > 0:
            LOGGER.info(f"{self.action} {source} to {target} ({bytes_to_human(size)})")

        call_process("ssh", hostname, "mkdir", "-p", shlex.quote(dest_path))
        # Only inject -n if the tool options don't already contain it.
        # (e.g. --tool '/path/to/mscp -n 64' must not get a second -n from --threads)
        n_flag = [] if "-n" in self._tool else ["-n", str(threads)] if threads > 1 else []
        call_process(*self._tool, *n_flag, source, f"{hostname}:{dest_path}")
        return size


class RsyncUpload(SshBaseUpload):
    _default_tool = "rsync -a --partial"

    def copy(self, source: str, target: str, *, verbosity: int = 1, threads: int = 1, **kwargs) -> None:
        """Copy a file or a folder from the source to the target location.

        Parameters
        ----------
        source : str
            The source location.
        target : str
            The target location.
        verbosity : int, optional
            The verbosity level, by default 1.
        threads : int, optional
            The number of parallel rsync processes for directory transfers, by default 1.
        kwargs : dict
            Forwarded to :meth:`transfer_file` for single-file transfers.
        """
        if os.path.isdir(source):
            hostname, path = self._parse_target(target)
            if verbosity > 0:
                LOGGER.info(f"{self.action} {source} to {target}")
            call_process("ssh", hostname, "mkdir", "-p", shlex.quote(path))
            if threads > 1:
                # Split the file list into chunks and run one rsync per chunk in parallel.
                # rsync has no native parallelism flag; --files-from lets us shard the work.
                all_files = [
                    os.path.relpath(os.path.join(root, f), source) for root, _, files in os.walk(source) for f in files
                ]
                if all_files:
                    chunk_size = -(len(all_files) // -threads)  # ceiling division
                    chunks = [all_files[i : i + chunk_size] for i in range(0, len(all_files), chunk_size)]

                    def _rsync_chunk(file_list, _hostname=hostname, _path=path, _source=source):
                        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                            f.write("\n".join(file_list))
                            fname = f.name
                        try:
                            call_process(
                                *self._tool,
                                f"--files-from={fname}",
                                _source.rstrip("/") + "/",
                                f"{_hostname}:{_path}",
                            )
                        finally:
                            os.unlink(fname)

                    with concurrent.futures.ThreadPoolExecutor(max_workers=len(chunks)) as executor:
                        try:
                            futures = [executor.submit(_rsync_chunk, chunk) for chunk in chunks]
                            with tqdm.tqdm(total=len(chunks), desc="rsync chunks", unit="chunk") as pbar:
                                for future in concurrent.futures.as_completed(futures):
                                    future.result()
                                    pbar.update(1)
                        except Exception:
                            executor.shutdown(wait=False, cancel_futures=True)
                            raise
            else:
                # Trailing slash on source tells rsync to copy the *contents* into path,
                # not to nest the directory itself under path.
                # run_process (not call_process) so rsync's own output reaches the terminal.
                run_process(
                    *self._tool,
                    source.rstrip("/") + "/",
                    f"{hostname}:{path}",
                )
        else:
            self.transfer_file(
                source=source,
                target=target,
                verbosity=verbosity,
                threads=threads,
                **kwargs,
            )

    def _transfer_file(
        self,
        source: str,
        target: str,
        overwrite: bool,
        resume: bool,
        verbosity: int,
        threads: int,
        checkpoint: dict = None,
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
        checkpoint : dict, optional
            Checkpoint information for the transfer.

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
            *self._tool,
            # it would be nice to avoid two ssh calls, but the following is not possible,
            # this is because it requires a shell command and would not be safe.
            # # f"--rsync-path='mkdir -p {os.path.dirname(path)} && rsync'",
            source,
            f"{hostname}:{path}",
        )
        return size


class ScpUpload(SshBaseUpload):
    _default_tool = "scp"

    def _transfer_file(
        self,
        source: str,
        target: str,
        overwrite: bool,
        resume: bool,
        verbosity: int,
        threads: int,
        checkpoint: dict = None,
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
        checkpoint : dict, optional
            Checkpoint information for the transfer.

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

        if checkpoint is None:
            checkpoint = self.prepare_checkpoint(source, target)
        remote_size = checkpoint.get("remote_sizes", {}).get(path)

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
        call_process(*self._tool, "-p", source, shlex.quote(f"{hostname}:{path}"))

        return size
