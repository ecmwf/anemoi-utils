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


class BaseTransfer:

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
    def run(self, source, target, **kwargs):
        raise NotImplementedError


class BaseDownload(BaseTransfer):
    action = "Downloading"

    @abstractmethod
    def run(self, source, target, **kwargs):
        raise NotImplementedError


class BaseUpload(BaseTransfer):
    action = "Uploading"

    def run(self, source, target, **kwargs):
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


def transfer(
    source,
    target,
    overwrite=False,
    resume=False,
    verbosity=1,
    threads=1,
    progress=None,
):
    """Parameters
    ----------
    source : str
        A path to a file or a folder to upload.
    target : str
        A URL to a file or a folder on S3. The url should start with 's3://'.
    overwrite : bool, optional
        If the data is alreay on S3 it will be overwritten, by default False
    resume : bool, optional
        If the data is alreay on S3 it will not be uploaded, unless the remote file
        has a different size, by default False
    verbosity : int, optional
        The level of verbosity, by default 1
    progress: callable, optional
        A callable that will be called with the number of files, the total size of the files, the total size
        transferred and a boolean indicating if the transfer has started. By default None
    threads : int, optional
        The number of threads to use when uploading a directory, by default 1
    """

    if target == ".":
        target = os.path.basename(source)

    if overwrite and os.path.exists(target):
        LOGGER.info(f"Deleting {target}")
        shutil.rmtree(target)

    cls = _find_transfer_class(source, target)

    if cls is None:
        raise TransferMethodNotImplementedError(f"Transfer from {source} to {target} is not implemented")

    transferer = cls()

    transferer.run(
        source,
        target,
        overwrite=overwrite,
        resume=resume,
        verbosity=verbosity,
        threads=threads,
        progress=progress,
    )


def _find_transfer_class(source, target):
    source_is_ssh = source.startswith("ssh://")
    target_is_ssh = target.startswith("ssh://")

    source_in_s3 = source.startswith("s3://")
    target_in_s3 = target.startswith("s3://")

    source_is_local = not source_is_ssh and not source_in_s3
    target_is_local = not target_is_ssh and not target_in_s3

    assert sum([target_is_ssh, target_is_local, target_in_s3]) == 1, (target_is_ssh, target_is_local, target_in_s3)
    assert sum([source_is_ssh, source_is_local, source_in_s3]) == 1, (source_is_ssh, source_is_local, source_in_s3)

    if source_is_ssh and target_is_local:  # local <- ssh
        # not implemented yet
        # from .ssh import download as func
        pass

    if source_is_local and target_is_ssh:  # local -> ssh
        from .ssh import RsyncUpload

        return RsyncUpload

    if source_in_s3 and target_is_local:  # local <- S3
        from .s3 import S3Download

        return S3Download

    if source_is_local and target_in_s3:  # local -> S3
        from .s3 import S3Upload

        return S3Upload

    return None
