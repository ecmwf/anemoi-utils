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


def _temporary_directory() -> str:
    """Return a temporary directory in which to download test data.

    Returns
    -------
    str
        The path to the temporary directory.
    """
    global TEMPORARY_DIRECTORY
    with lock:
        if TEMPORARY_DIRECTORY is not None:
            return TEMPORARY_DIRECTORY

        TEMPORARY_DIRECTORY = tempfile.mkdtemp()

        # Register a cleanup function to remove the directory at exit
        atexit.register(shutil.rmtree, TEMPORARY_DIRECTORY)

        return TEMPORARY_DIRECTORY


def _check_path(path: str) -> None:
    """Check if the given path is normalized, not absolute, and does not start with a dot.

    Parameters
    ----------
    path : str
        The path to check.

    Raises
    ------
    AssertionError
        If the path is not normalized, is absolute, or starts with a dot.
    """
    assert os.path.normpath(path) == path, f"Path '{path}' should be normalized"
    assert not os.path.isabs(path), f"Path '{path}' should not be absolute"
    assert not path.startswith("."), f"Path '{path}' should not start with '.'"


def url_for_test_data(path: str) -> str:
    """Generate the URL for the test data based on the given path.

    Parameters
    ----------
    path : str
        The relative path to the test data.

    Returns
    -------
    str
        The full URL to the test data.
    """
    _check_path(path)

    return f"{TEST_DATA_URL}{path}"


def get_test_data(path: str) -> str:
    """Download the test data to a temporary directory and return the local path.

    Parameters
    ----------
    path : str
        The relative path to the test data.

    Returns
    -------
    str
        The local path to the downloaded test data.
    """
    _check_path(path)

    target = os.path.normpath(os.path.join(_temporary_directory(), path))
    with lock:
        if os.path.exists(target):
            return target

        os.makedirs(os.path.dirname(target), exist_ok=True)
        url = url_for_test_data(path)
        LOG.info(f"Downloading test data from {url} to {target}")

        download(url, target)
        return target
