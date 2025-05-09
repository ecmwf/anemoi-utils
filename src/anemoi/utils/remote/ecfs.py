# (C) Copyright 2025 Anemoi contributors.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
import os
import shutil
import subprocess
import tarfile
import time

import dateparser
import tqdm

from anemoi.utils.humanize import bytes_to_human

LOG = logging.getLogger(__name__)


def ecfs_stat(path: str) -> dict:
    """Get the status of a file or directory on the ECFS system.

    Parameters
    ----------
    path : str
        The path to the file or directory.

    Returns
    -------
    dict
        A dictionary containing the status information.
    """

    if "://" in path:
        scheme, path = path.split("://", 1)
        path = f"{scheme}:/{path}"

    cmd = ["els", "-l", path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if "File does not exist" in result.stderr:
            return None

        raise RuntimeError(f"Failed to get status for {path}: {result.stderr}")

    flags, inodes, user, group, size, date1, date2, date3, name = result.stdout.split()
    size = int(size)
    date = dateparser.parse(f"{date1} {date2} {date3}")

    return {
        "flags": flags,
        "inodes": inodes,
        "user": user,
        "group": group,
        "size": size,
        "date": date,
        "name": name,
    }


class EcfsDownload:
    # def get_temporary_target(self, target: str, pattern: str) -> str:
    #     pass
    def get_temporary_target(self, target: str, pattern: str) -> str:
        return target

    def copy(self, source: str, target: str, workdir: str, overwrite: bool = False, **kwargs: dict) -> None:
        if source.endswith(".tar"):
            return self.copy_tar(source, target, workdir, overwrite, **kwargs)
        return self.copy_file(source, target, workdir, overwrite, **kwargs)

    def delete_target(self, target: str) -> None:
        # Will do it elsewhere
        pass

    def copy_tar(self, source: str, target: str, workdir: str, overwrite: bool = False, **kwargs: dict) -> None:
        target = os.path.realpath(target)
        workdir = os.path.realpath(workdir)
        LOG.info(f"Using workdir {workdir}")

        if target.endswith("/"):
            os.makedirs(target, exist_ok=True)

        if os.path.exists(target) and os.path.isdir(target):
            target = os.path.join(target, os.path.basename(source))

        if target.endswith(".tar"):
            target = target[:-4]

        if os.path.exists(target):
            if not overwrite:
                raise FileExistsError(f"Target file {target} already exists. Please use --overwrite.")
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)

        scheme, path = source.split("://", 1)
        tar = os.path.join(workdir, os.path.basename(source))

        target_root = os.path.basename(target)
        target_dir = os.path.dirname(target)

        try:

            tar = self.copy_file(source, tar, workdir, overwrite, **kwargs)

            size = os.path.getsize(tar)
            now = time.time()
            with tqdm.tqdm(
                total=size, unit_divisor=1024, unit_scale=True, desc="Extracting tar file", leave=False
            ) as pbar:

                def progress_filter(tarinfo, path):

                    root, *rest = tarinfo.name.split("/")

                    if root != target_root:
                        raise ValueError(f"Root {root} in tar does not match path {target_root} ({tarinfo.name})")

                    pbar.update(tarinfo.size)
                    return tarinfo

                with tarfile.open(tar, "r") as f:
                    f.extractall(target_dir, filter=progress_filter)

            elapsed = time.time() - now
            LOG.info(f"Extracted tar file {tar} ({bytes_to_human(os.path.getsize(tar)/elapsed)}/s)")

        finally:
            if os.path.exists(tar):
                LOG.info(f"Removing temporary tar file {tar}")
                os.remove(tar)

        LOG.info(f"{target} ready")

    def copy_file(self, source: str, target: str, workdir: str, overwrite: bool = False, **kwargs: dict) -> None:
        """Copy a file to the target location using ecfs.
        Parameters
        ----------
        source : str

            The source file path.
        target : str
            The target file path.
        workdir : str
            The working directory path.
        overwrite : bool, optional
            Whether to overwrite the target file if it exists, by default False.
        **kwargs : dict
            Additional keyword arguments.
        """
        scheme, path = source.split("://", 1)

        if target.endswith("/"):
            os.makedirs(target, exist_ok=True)

        if os.path.exists(target) and os.path.isdir(target):
            target = os.path.join(target, os.path.basename(source))
            if os.path.exists(target):
                if not overwrite:
                    raise FileExistsError(f"Target file {target} already exists. Please use --overwrite.")
                if os.path.isdir(target):
                    shutil.rmtree(target)
                else:
                    os.remove(target)

        cmd = [
            "ecp",
            "-o",  # Overwrite
            f"{scheme}:/{path}",
            target,
        ]
        LOG.info(f"Downloading {source} to {target}")
        LOG.info(f"Running command: {' '.join(cmd)}")
        now = time.time()
        subprocess.run(cmd, check=True)
        elapsed = time.time() - now
        size = os.path.getsize(target)
        LOG.info(f"Downloaded {source} to {target} (size {bytes_to_human(size)} at {bytes_to_human(size/elapsed)}/s)")

        return target


class EcfsUpload:

    def get_temporary_target(self, target: str, pattern: str) -> str:
        return target

    def rename_target(self, target: str, temporary_target: str) -> None:
        assert target == temporary_target, "Renaming is not supported for ecfs uploads"

    def delete_target(self, target: str) -> None:
        # Will use -o to overwrite the target
        pass

    def copy(self, source: str, target: str, workdir: str, overwrite: bool = False, **kwargs: dict) -> None:
        """Copy a file to the target location using ecfs.

        Parameters
        ----------
        source : str
            The source file path.
        target : str
            The target file path.
        workdir : str
            The working directory path.
        overwrite : bool, optional
            Whether to overwrite the target file if it exists, by default False.
        **kwargs : dict
            Additional keyword arguments.
        """

        if os.path.isdir(source):
            return self.copy_dir(source, target, workdir, overwrite, **kwargs)

        return self.copy_file(source, target, workdir, overwrite, **kwargs)

    def copy_dir(self, source: str, target: str, workdir: str, overwrite: bool = False, **kwargs: dict) -> None:
        """Copy a directory to the target location using ecfs.

        Parameters
        ----------
        source : str
            The source directory path.
        target : str
            The target file path.
        workdir : str
            The working directory path.
        overwrite : bool, optional
            Whether to overwrite the target file if it exists, by default False.
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
            if not overwrite:
                raise FileExistsError(f"Tar file {tar} already exists. Use --overwrite.")
            os.remove(tar)

        try:
            LOG.info(f"Creating tar file {tar} with {count} files")

            ref = os.path.dirname(source)

            now = time.time()
            with tarfile.open(tar, "w", bufsize=1024 * 1024 * 64) as f:
                for file in tqdm.tqdm(scan(source), desc="Creating tar file", unit="file", total=count, leave=False):
                    f.add(file, arcname=os.path.relpath(file, ref))
            elapsed = time.time() - now
            LOG.info(f"Created tar file {tar} ({bytes_to_human(os.path.getsize(tar)/elapsed)}/s)")

            self.copy_file(tar, target, workdir, overwrite, **kwargs)

        finally:
            if os.path.exists(tar):
                os.remove(tar)

    def copy_file(self, source: str, target: str, workdir: str, overwrite, **kwargs: dict) -> None:
        """Copy a file to the target location using ecfs.

        Parameters
        ----------
        source : str
            The source file path.
        target : str
            The target file path.
        workdir : str
            The working directory path.
        overwrite : bool, optional
            Whether to overwrite the target file if it exists, by default False.
        **kwargs : dict
            Additional keyword arguments.
        """
        scheme, path = target.split("://", 1)
        cmd = [
            "ecp",
            "-o" if overwrite else "-e",  # Overwrite or fail if exists
            "-b",  # Create a backup copy in the disaster recovery system
            source,
            f"{scheme}:/{path}",
        ]

        size = os.path.getsize(source)
        LOG.info(f"Uploading {source} to {target} (size {bytes_to_human(size)})")
        LOG.info(f"Running command: {' '.join(cmd)}")
        now = time.time()
        subprocess.run(cmd, check=True)
        elapsed = time.time() - now
        LOG.info(f"Uploaded {source} to {target} ({bytes_to_human(size/elapsed)}/s)")


if __name__ == "__main__":
    print(ecfs_stat("ectmp:/mab/test.tar"))
