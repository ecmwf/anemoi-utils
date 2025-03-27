# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import concurrent.futures
import logging
import os
import shutil
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import Iterable

import tqdm

from ..humanize import bytes_to_human

LOGGER = logging.getLogger(__name__)


def robust(call: callable, *args, maximum_tries: int = 60, retry_after: int = 60, **kwargs) -> callable:
    """Forwards the arguments to the multiurl robust function.
    with default retry_after=60 and maximum_tries=60.
    """
    from multiurl import robust as robust_

    return robust_(call, *args, retry_after=retry_after, maximum_tries=maximum_tries, **kwargs)


def _ignore(number_of_files: int, total_size: int, total_transferred: int, transfering: bool) -> None:
    """A placeholder function for progress reporting.

    Parameters
    ----------
    number_of_files : int
        The number of files being transferred.
    total_size : int
        The total size of the files being transferred.
    total_transferred : int
        The total size of the files transferred so far.
    transfering : bool
        Whether the transfer is in progress.
    """
    pass


class Loader:
    def transfer_folder(
        self,
        *,
        source: str,
        target: str,
        overwrite: bool = False,
        resume: bool = False,
        verbosity: int = 1,
        threads: int = 1,
        progress: callable = None,
    ) -> None:
        """Transfer a folder from the source to the target location.

        Parameters
        ----------
        source : str
            The source folder path.
        target : str
            The target folder path.
        overwrite : bool, optional
            Whether to overwrite the target if it exists, by default False.
        resume : bool, optional
            Whether to resume the transfer if possible, by default False.
        verbosity : int, optional
            The verbosity level, by default 1.
        threads : int, optional
            The number of threads to use, by default 1.
        progress : callable, optional
            A callable for progress reporting, by default None.
        """
        assert verbosity == 1, verbosity

        if progress is None:
            progress = _ignore

        # from boto3.s3.transfer import TransferConfig
        # config = TransferConfig(use_threads=False)
        config = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            try:
                if verbosity > 0:
                    LOGGER.info(f"{self.action} {source} to {target}")

                total_size = 0
                total_transferred = 0

                futures = []
                for name in self.list_source(source):

                    futures.append(
                        executor.submit(
                            self.transfer_file,
                            source=self.source_path(name, source),
                            target=self.target_path(name, source, target),
                            overwrite=overwrite,
                            resume=resume,
                            verbosity=verbosity - 1,
                            config=config,
                        )
                    )
                    total_size += self.source_size(name)

                    if len(futures) % 10000 == 0:

                        progress(len(futures), total_size, 0, False)

                        if verbosity > 0:
                            LOGGER.info(f"Preparing transfer, {len(futures):,} files... ({bytes_to_human(total_size)})")
                        done, _ = concurrent.futures.wait(
                            futures,
                            timeout=0.001,
                            return_when=concurrent.futures.FIRST_EXCEPTION,
                        )
                        # Trigger exceptions if any
                        for future in done:
                            future.result()

                number_of_files = len(futures)
                progress(number_of_files, total_size, 0, True)

                if verbosity > 0:
                    LOGGER.info(f"{self.action} {number_of_files:,} files ({bytes_to_human(total_size)})")
                    with tqdm.tqdm(total=total_size, unit="B", unit_scale=True, unit_divisor=1024) as pbar:
                        for future in concurrent.futures.as_completed(futures):
                            size = future.result()
                            pbar.update(size)
                            total_transferred += size
                            progress(number_of_files, total_size, total_transferred, True)
                else:
                    for future in concurrent.futures.as_completed(futures):
                        size = future.result()
                        total_transferred += size
                        progress(number_of_files, total_size, total_transferred, True)

            except Exception:
                executor.shutdown(wait=False, cancel_futures=True)
                raise

    def transfer_file(
        self,
        source: str,
        target: str,
        overwrite: bool,
        resume: bool,
        verbosity: int,
        threads: int = 1,
        progress: callable = None,
        config: dict = None,
    ) -> int:
        """Transfer a file from the source to the target location.

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
        threads : int, optional
            The number of threads to use, by default 1.
        progress : callable, optional
            A callable for progress reporting, by default None.
        config : dict, optional
            Additional configuration options, by default None.

        Returns
        -------
        int
            The size of the transferred file.

        Raises
        ------
        Exception
            If an error occurs during the transfer.
        """
        try:
            return self._transfer_file(source, target, overwrite, resume, verbosity, threads=threads, config=config)
        except Exception as e:
            LOGGER.exception(f"Error transferring {source} to {target}")
            LOGGER.error(e)
            raise

    @abstractmethod
    def list_source(self, source: str) -> Iterable:
        """List the files in the source location.

        Parameters
        ----------
        source : str
            The source location.

        Returns
        -------
        Iterable
            An iterable of files in the source location.
        """
        raise NotImplementedError

    @abstractmethod
    def source_path(self, local_path: str, source: str) -> str:
        """Get the source path for a local file.

        Parameters
        ----------
        local_path : str
            The local file path.
        source : str
            The source location.

        Returns
        -------
        str
            The source path for the local file.
        """
        raise NotImplementedError

    @abstractmethod
    def target_path(self, source_path: str, source: str, target: str) -> str:
        """Get the target path for a source file.

        Parameters
        ----------
        source_path : str
            The source file path.
        source : str
            The source location.
        target : str
            The target location.

        Returns
        -------
        str
            The target path for the source file.
        """
        raise NotImplementedError

    @abstractmethod
    def source_size(self, local_path: str) -> int:
        """Get the size of a local file.

        Parameters
        ----------
        local_path : str
            The local file path.

        Returns
        -------
        int
            The size of the local file.
        """
        raise NotImplementedError

    @abstractmethod
    def copy(self, source: str, target: str, **kwargs) -> None:
        """Copy a file or folder from the source to the target location.

        Parameters
        ----------
        source : str
            The source location.
        target : str
            The target location.
        kwargs : dict
            Additional arguments for the transfer.
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def rename_target(self, target: str, temporary_target: str) -> None:
        """Rename the target to a new target path.

        Parameters
        ----------
        target : str
            The original target path.
        temporary_target : str
            The new target path.
        """
        raise NotImplementedError


class BaseDownload(Loader):
    action = "Downloading"

    @abstractmethod
    def copy(self, source: str, target: str, **kwargs) -> None:
        """Copy a file or folder from the source to the target location.

        Parameters
        ----------
        source : str
            The source location.
        target : str
            The target location.
        kwargs : dict
            Additional arguments for the transfer.
        """
        raise NotImplementedError

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
        if pattern is None:
            return target
        dirname, basename = os.path.split(target)
        return pattern.format(dirname=dirname, basename=basename)

    def rename_target(self, target: str, new_target: str) -> None:
        """Rename the target to a new target path.

        Parameters
        ----------
        target : str
            The original target path.
        new_target : str
            The new target path.
        """
        os.rename(target, new_target)

    def delete_target(self, target: str) -> None:
        """Delete the target if it exists.

        Parameters
        ----------
        target : str
            The target path.
        """
        if os.path.exists(target):
            shutil.rmtree(target)


class BaseUpload(Loader):
    action = "Uploading"

    def copy(self, source: str, target: str, **kwargs) -> None:
        """Copy a file or folder from the source to the target location.

        Parameters
        ----------
        source : str
            The source location.
        target : str
            The target location.
        kwargs : dict
            Additional arguments for the transfer.
        """
        if os.path.isdir(source):
            self.transfer_folder(source=source, target=target, **kwargs)
        else:
            self.transfer_file(source=source, target=target, **kwargs)

    def list_source(self, source: str) -> Iterable:
        """List the files in the source location.

        Parameters
        ----------
        source : str
            The source location.

        Returns
        -------
        Iterable
            An iterable of files in the source location.
        """
        for root, _, files in os.walk(source):
            for file in files:
                yield os.path.join(root, file)

    def source_path(self, local_path: str, source: str) -> str:
        """Get the source path for a local file.

        Parameters
        ----------
        local_path : str
            The local file path.
        source : str
            The source location.

        Returns
        -------
        str
            The source path for the local file.
        """
        return local_path

    def target_path(self, source_path: str, source: str, target: str) -> str:
        """Get the target path for a source file.

        Parameters
        ----------
        source_path : str
            The source file path.
        source : str
            The source location.
        target : str
            The target location.

        Returns
        -------
        str
            The target path for the source file.
        """
        relative_path = os.path.relpath(source_path, source)
        path = os.path.join(target, relative_path)
        return path

    def source_size(self, local_path: str) -> int:
        """Get the size of a local file.

        Parameters
        ----------
        local_path : str
            The local file path.

        Returns
        -------
        int
            The size of the local file.
        """
        return os.path.getsize(local_path)


class TransferMethodNotImplementedError(NotImplementedError):
    pass


class Transfer:
    """This is the internal API and should not be used directly. Use the transfer function instead."""

    TransferMethodNotImplementedError = TransferMethodNotImplementedError

    def __init__(
        self,
        *,
        source: str,
        target: str,
        overwrite: bool = False,
        resume: bool = False,
        verbosity: int = 1,
        threads: int = 1,
        progress: callable = None,
        temporary_target: bool = False,
    ):
        if target == ".":
            target = os.path.basename(source)
            if not target:
                target = os.path.basename(os.path.dirname(source))

        temporary_target: Dict[Any, Any] = {
            False: None,
            True: "{dirname}-downloading/{basename}",
            "-tmp/*": "{dirname}-tmp/{basename}",
            "*-tmp": "{dirname}/{basename}-tmp",
            "tmp-*": "{dirname}/tmp-{basename}",
        }.get(temporary_target, temporary_target)
        assert temporary_target is None or isinstance(temporary_target, str), (type(temporary_target), temporary_target)

        self.source = source
        self.target = target
        self.overwrite = overwrite
        self.resume = resume
        self.verbosity = verbosity
        self.threads = threads
        self.progress = progress
        self.temporary_target = temporary_target

        cls = _find_transfer_class(self.source, self.target)
        self.loader = cls()

    def run(self) -> "Transfer":
        """Execute the transfer process.

        Returns
        -------
        Transfer
            The Transfer instance.
        """
        target = self.loader.get_temporary_target(self.target, self.temporary_target)
        if target != self.target:
            LOGGER.info(f"Using temporary target {target} to copy to {self.target}")

        if self.overwrite:
            # delete the target if it exists
            LOGGER.info(f"Deleting {self.target}")
            self.delete_target(target)

            # carefully delete the temporary target if it exists
            head, tail = os.path.split(self.target)
            head_, tail_ = os.path.split(target)
            if not head_.startswith(head) or tail not in tail_:
                LOGGER.info(f"{target} is too different from {self.target} to delete it automatically.")
            else:
                self.delete_target(target)

        self.loader.copy(
            self.source,
            target,
            overwrite=self.overwrite,
            resume=self.resume,
            verbosity=self.verbosity,
            threads=self.threads,
            progress=self.progress,
        )

        self.rename_target(target, self.target)

        return self

    def rename_target(self, target: str, new_target: str) -> None:
        """Rename the target to a new target path.

        Parameters
        ----------
        target : str
            The original target path.
        new_target : str
            The new target path.
        """
        if target != new_target:
            LOGGER.info(f"Renaming temporary target {target} into {self.target}")
            return self.loader.rename_target(target, new_target)

    def delete_target(self, target: str) -> None:
        """Delete the target if it exists.

        Parameters
        ----------
        target : str
            The target path.
        """
        return self.loader.delete_target(target)


def _find_transfer_class(source: str, target: str) -> type:
    """Find the appropriate transfer class based on the source and target locations.

    Parameters
    ----------
    source : str
        The source location.
    target : str
        The target location.

    Returns
    -------
    type
        The transfer class.

    Raises
    ------
    TransferMethodNotImplementedError
        If the transfer method is not implemented.
    """
    from_ssh = source.startswith("ssh://")
    into_ssh = target.startswith("ssh://")

    from_s3 = source.startswith("s3://")
    into_s3 = target.startswith("s3://")

    from_local = not from_ssh and not from_s3
    into_local = not into_ssh and not into_s3

    # check that exactly one source type and one target type is specified
    assert sum([into_ssh, into_local, into_s3]) == 1, (into_ssh, into_local, into_s3)
    assert sum([from_ssh, from_local, from_s3]) == 1, (from_ssh, from_local, from_s3)

    if from_local and into_ssh:  # local -> ssh
        from .ssh import RsyncUpload

        return RsyncUpload

    if from_s3 and into_local:  # local <- S3
        from .s3 import S3Download

        return S3Download

    if from_local and into_s3:  # local -> S3
        from .s3 import S3Upload

        return S3Upload

    raise TransferMethodNotImplementedError(f"Transfer from {source} to {target} is not implemented")


# This function is the main entry point for the transfer mechanism for the other anemoi packages
def transfer(
    source, target, *, overwrite=False, resume=False, verbosity=1, progress=None, threads=1, temporary_target=False
) -> Loader:
    """Transfer files or folders from the source to the target location.

    Parameters
    ----------
    source : str
        A path to a local file or folder or a URL to a file or a folder on S3.
        The url should start with 's3://'.
    target : str
        A path to a local file or folder or a URL to a file or a folder on S3 or a remote folder.
        The url should start with 's3://' or 'ssh://'.
    overwrite : bool, optional
        If the data is alreay on in the target location it will be overwritten.
        By default False
    resume : bool, optional
        If the data is alreay on S3 it will not be uploaded, unless the remote file has a different size
        Ignored if the target is an SSH remote folder (ssh://).
        By default False
    verbosity : int, optional
        The level of verbosity, by default 1
    progress : callable, optional
        A callable that will be called with the number of files, the total size of the files, the total size
        transferred and a boolean indicating if the transfer has started. By default None
    threads : int, optional
        The number of threads to use when uploading a directory, by default 1
    temporary_target : bool, optional
        Experimental feature
        If True and if the target location supports it, the data will be uploaded to a temporary location
        then renamed to the final location. Supported by SSH and local targets, not supported by S3.
        By default False.

    Returns
    -------
    Loader
        The Loader instance.
    """
    copier = Transfer(
        source=source,
        target=target,
        overwrite=overwrite,
        resume=resume,
        verbosity=verbosity,
        progress=progress,
        threads=threads,
        temporary_target=temporary_target,
    )
    copier.run()
    return copier
