# (C) Copyright 2025- Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import atexit
import logging
import os
import shutil
import tempfile
import threading

from multiurl import download

LOG = logging.getLogger(__name__)

TEST_DATA_URL = "https://object-store.os-api.cci1.ecmwf.int/ml-tests/test-data/samples/"

lock = threading.Lock()
TEMPORARY_DIRECTORY = None


def temporary_directory() -> str:
    """Return a temporary in which to download test data."""
    global TEMPORARY_DIRECTORY
    with lock:
        if TEMPORARY_DIRECTORY is not None:
            return TEMPORARY_DIRECTORY

        TEMPORARY_DIRECTORY = tempfile.mkdtemp()

        # Register a cleanup function to remove the directory at exit
        atexit.register(shutil.rmtree, TEMPORARY_DIRECTORY)

        return TEMPORARY_DIRECTORY


def get_test_data(path: str) -> str:
    assert os.path.normpath(path) == path, f"Path '{path}' should be normalized"
    assert not os.path.isabs(path), f"Path '{path}' should not be absolute"
    assert not path.startswith("."), f"Path '{path}' should not start with '.'"

    target = os.path.normpath(os.path.join(temporary_directory(), path))
    with lock:
        if os.path.exists(target):
            return target

        os.makedirs(os.path.dirname(target), exist_ok=True)
        url = f"{TEST_DATA_URL}{path}"
        LOG.info(f"Downloading test data from {url} to {target}")

        download(url, target)
        return target
