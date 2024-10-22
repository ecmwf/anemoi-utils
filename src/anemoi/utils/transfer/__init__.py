# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import concurrent.futures
import logging
import os

import tqdm

from ..humanize import bytes_to_human

LOGGER = logging.getLogger(__name__)


def _ignore(number_of_files, total_size, total_transferred, transfering):
    pass


class Transfer:

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


class BaseUpload(Transfer):
    action = "Uploading"

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

    def transfer_file(self, source, target, overwrite, resume, verbosity, progress=None, config=None):
        try:
            return self._transfer_file(source, target, overwrite, resume, verbosity, config=config)
        except Exception as e:
            LOGGER.exception(f"Error transferring {source} to {target}")
            LOGGER.error(e)
            raise
