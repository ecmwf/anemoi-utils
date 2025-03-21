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

lock = threading.RLock()
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


def get_test_data(path: str, gzipped=False) -> str:
    """Download the test data to a temporary directory and return the local path.

    Parameters
    ----------
    path : str
        The relative path to the test data.
    gzipped : bool, optional
        Flag indicating if the remote file is gzipped, by default False. The local file will be gunzipped.

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

        if gzipped:
            url += ".gz"
            target += ".gz"

        LOG.info(f"Downloading test data from {url} to {target}")

        download(url, target)

        if gzipped:
            import gzip

            with gzip.open(target, "rb") as f_in:
                with open(target[:-3], "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(target)
            target = target[:-3]

        return target


def get_test_archive(path: str, extension=".extracted") -> str:
    """Download an archive file (.zip, .tar, .tar.gz, .tar.bz2, .tar.xz) to a temporary directory
    unpack it, and return the local path to the directory containing the extracted files.

    Parameters
    ----------
    path : str
        The relative path to the test data.
    extension : str, optional
        The extension to add to the extracted directory, by default '.extracted'

    Returns
    -------
    str
        The local path to the downloaded test data.
    """

    with lock:

        archive = get_test_data(path)
        target = archive + extension

        shutil.unpack_archive(archive, os.path.dirname(target) + ".tmp")
        os.rename(os.path.dirname(target) + ".tmp", target)

        return target


def packages_installed(*names) -> bool:
    """Check if all the given packages are installed.

    Use this function to check if the required packages are installed before running tests.

    >>> @pytest.mark.skipif(not packages_installed("foo", "bar"), reason="Packages 'foo' and 'bar' are not installed")
    >>> def test_foo_bar() -> None:
    >>>    ...

    Parameters
    ----------
    names : str
        The names of the packages to check.

    Returns
    -------
    bool:
        Flag indicating if all the packages are installed."
    """

    for name in names:
        try:
            __import__(name)
        except ImportError:
            return False
    return True
