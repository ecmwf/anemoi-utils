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

import tqdm

from ..humanize import bytes_to_human

LOGGER = logging.getLogger(__name__)


def _ignore(number_of_files, total_size, total_transferred, transfering):
    pass


class Loader:

    def transfer_folder(self, *, source, target, overwrite=False, resume=False, verbosity=1, threads=1, progress=None):
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

    def transfer_file(self, source, target, overwrite, resume, verbosity, threads=1, progress=None, config=None):
        try:
            return self._transfer_file(source, target, overwrite, resume, verbosity, threads=threads, config=config)
        except Exception as e:
            LOGGER.exception(f"Error transferring {source} to {target}")
            LOGGER.error(e)
            raise

    @abstractmethod
    def list_source(self, source):
        raise NotImplementedError

    @abstractmethod
    def source_path(self, local_path, source):
        raise NotImplementedError

    @abstractmethod
    def target_path(self, source_path, source, target):
        raise NotImplementedError

    @abstractmethod
    def source_size(self, local_path):
        raise NotImplementedError

    @abstractmethod
    def copy(self, source, target, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_temporary_target(self, target, pattern):
        raise NotImplementedError

    @abstractmethod
    def rename_target(self, target, temporary_target):
        raise NotImplementedError


class BaseDownload(Loader):
    action = "Downloading"

    @abstractmethod
    def copy(self, source, target, **kwargs):
        raise NotImplementedError

    def get_temporary_target(self, target, pattern):
        if pattern is None:
            return target
        dirname, basename = os.path.split(target)
        return pattern.format(dirname=dirname, basename=basename)

    def rename_target(self, target, new_target):
        os.rename(target, new_target)

    def delete_target(self, target):
        if os.path.exists(target):
            shutil.rmtree(target)


class BaseUpload(Loader):
    action = "Uploading"

    def copy(self, source, target, **kwargs):
        if os.path.isdir(source):
            self.transfer_folder(source=source, target=target, **kwargs)
        else:
            self.transfer_file(source=source, target=target, **kwargs)

    def list_source(self, source):
        for root, _, files in os.walk(source):
            for file in files:
                yield os.path.join(root, file)

    def source_path(self, local_path, source):
        return local_path

    def target_path(self, source_path, source, target):
        relative_path = os.path.relpath(source_path, source)
        path = os.path.join(target, relative_path)
        return path

    def source_size(self, local_path):
        return os.path.getsize(local_path)


class TransferMethodNotImplementedError(NotImplementedError):
    pass


class Transfer:
    """This is the internal API and should not be used directly. Use the transfer function instead."""

    TransferMethodNotImplementedError = TransferMethodNotImplementedError

    def __init__(
        self,
        source,
        target,
        overwrite=False,
        resume=False,
        verbosity=1,
        threads=1,
        progress=None,
        temporary_target=False,
    ):
        if target == ".":
            target = os.path.basename(source)

        temporary_target = {
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

    def run(self):

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

    def rename_target(self, target, new_target):
        if target != new_target:
            LOGGER.info(f"Renaming temporary target {target} into {self.target}")
            return self.loader.rename_target(target, new_target)

    def delete_target(self, target):
        return self.loader.delete_target(target)


def _find_transfer_class(source, target):
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


# this is the public API
def transfer(*args, **kwargs) -> Loader:
    """Parameters
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
    progress: callable, optional
        A callable that will be called with the number of files, the total size of the files, the total size
        transferred and a boolean indicating if the transfer has started. By default None
    threads : int, optional
        The number of threads to use when uploading a directory, by default 1
    temporary_target : bool, optional
        Experimental feature
        If True and if the target location supports it, the data will be uploaded to a temporary location
        then renamed to the final location. Supported by SSH and local targets, not supported by S3.
        By default False
    """
    copier = Transfer(*args, **kwargs)
    copier.run()
    return copier
