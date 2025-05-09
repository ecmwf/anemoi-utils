# (C) Copyright 2025 Anemoi contributors.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
import os
import subprocess
import tarfile

import tqdm

from ..humanize import bytes_to_human

LOG = logging.getLogger(__name__)


class EcfsDownload:
    # def get_temporary_target(self, target: str, pattern: str) -> str:
    #     pass
    def get_temporary_target(self, target: str, pattern: str) -> str:
        return target


class EcfsUpload:

    def get_temporary_target(self, target: str, pattern: str) -> str:
        return target

    def rename_target(self, target: str, temporary_target: str) -> None:
        assert target == temporary_target, "Renaming is not supported for ecfs uploads"

    def copy(self, source: str, target: str, workdir: str, **kwargs: dict) -> None:
        """Copy a file to the target location using ecfs.

        Parameters
        ----------
        source : str
            The source file path.
        target : str
            The target file path.
        workdir : str
            The working directory path.
        **kwargs : dict
            Additional keyword arguments.
        """

        if os.path.isdir(source):
            return self.copy_dir(source, target, workdir, **kwargs)

        return self.copy_file(source, target, workdir, **kwargs)

    def copy_dir(self, source: str, target: str, workdir: str, **kwargs: dict) -> None:
        """Copy a directory to the target location using ecfs.

        Parameters
        ----------
        source : str
            The source directory path.
        target : str
            The target file path.
        workdir : str
            The working directory path.
        **kwargs : dict
            Additional keyword arguments.
        """
        source = os.path.realpath(source)
        workdir = os.path.realpath(workdir)
        LOG.info(f"Using workdir {workdir}")

        def scan(source: str) -> int:
            """Scan the source directory and yield file paths.

            Parameters
            ----------
            source : str
                The source directory path.

            Yields
            ------
            str
                File paths within the source directory.
            """
            for root, dirs, files in os.walk(source):
                for file in files:
                    yield os.path.join(root, file)

        count = 0
        for _ in scan(source):
            count += 1

        tar = os.path.join(workdir, os.path.basename(source) + ".tar")
        if os.path.exists(tar):
            raise FileExistsError(f"Tar file {tar} already exists. Please remove it before uploading.")

        try:
            LOG.info(f"Creating tar file {tar} with {count} files")

            ref = os.path.dirname(source)

            with tarfile.open(tar, "w", bufsize=1024 * 1024 * 64) as f:
                for file in tqdm.tqdm(scan(source), desc="Creating tar file", unit="file", total=count):
                    f.add(file, arcname=os.path.relpath(file, ref))

            self.copy_file(tar, target, workdir, **kwargs)

        finally:
            if os.path.exists(tar):
                os.remove(tar)

    def copy_file(self, source: str, target: str, workdir: str, **kwargs: dict) -> None:
        """Copy a file to the target location using ecfs.

        Parameters
        ----------
        source : str
            The source file path.
        target : str
            The target file path.
        workdir : str
            The working directory path.
        **kwargs : dict
            Additional keyword arguments.
        """
        scheme, path = target.split("://", 1)
        cmd = [
            "ecp",
            "-o",  # Overwrite
            "-b",  # Create a backup copy in the disaster recovery system
            source,
            f"{scheme}:/{path}",
        ]
        LOG.info(f"Uploading {source} to {target} (size {bytes_to_human(os.path.getsize(source))})")
        LOG.info(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
