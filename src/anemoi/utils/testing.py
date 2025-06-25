# (C) Copyright 2025- Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
import os
import shutil
import warnings
from functools import lru_cache
from pathlib import Path

import pytest
from multiurl import download

from anemoi.utils.humanize import list_to_human

LOG = logging.getLogger(__name__)

TEST_DATA_URL = "https://object-store.os-api.cci1.ecmwf.int/ml-tests/test-data/samples/"


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


@pytest.fixture(scope="session")
def temporary_directory_for_test_data(tmp_path_factory) -> callable:
    base_dir = tmp_path_factory.mktemp("test_data_base")

    def _temporary_directory_for_test_data(path: str = "", archive: bool = False) -> str:
        if path == "":
            return str(base_dir)
        _check_path(path)
        return str(base_dir.joinpath(*Path(path).parts)) + (".extracted" if archive else "")

    return _temporary_directory_for_test_data


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


@pytest.fixture()
def get_test_data(temporary_directory_for_test_data):
    def _get_test_data(path: str, gzipped=False) -> callable:
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

        if _offline():
            raise RuntimeError("Offline mode: cannot download test data, add @pytest.mark.skipif(not offline(),...)")

        target = temporary_directory_for_test_data(path)

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

    return _get_test_data


@pytest.fixture()
def get_test_archive(temporary_directory_for_test_data, get_test_data) -> callable:
    def _get_test_archive(path: str) -> str:
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

        target = Path(temporary_directory_for_test_data(path, archive=True))

        if os.path.exists(target):
            return target

        archive = get_test_data(path)

        shutil.unpack_archive(archive, os.path.dirname(target) + ".tmp")
        os.rename(os.path.dirname(target) + ".tmp", target)

        os.remove(archive)

        return target

    return _get_test_archive


def packages_installed(*names: str) -> bool:
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

    warnings.warn(
        "The 'packages_installed' function is deprecated. Use '@skip_if_missing' instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    for name in names:
        try:
            __import__(name)
        except ImportError:
            return False
    return True


def _missing_packages(*names: str) -> list[str]:
    """Check if the given packages are missing.

    Use this function to check if the required packages are missing before running tests.

    >>> @pytest.mark.skipif(missing_packages("foo", "bar"), reason="Packages 'foo' and 'bar' are not installed")
    >>> def test_foo_bar() -> None:
    >>>    ...

    Parameters
    ----------
    names : str
        The names of the packages to check.

    Returns
    -------
    list[str]:
        List of missing packages.
    """

    missing = []
    for name in names:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    return missing


def _run_slow_tests() -> bool:
    """Check if the SLOW_TESTS environment variable is set.

    Returns
    -------
    bool
        True if the SLOW_TESTS environment variable is set, False otherwise.
    """
    return int(os.environ.get("SLOW_TESTS", 0))


@lru_cache(maxsize=None)
def _offline() -> bool:
    """Check if we are offline."""
    from urllib import request

    try:
        request.urlopen("https://anemoi.ecmwf.int", timeout=1)
        return False
    except request.URLError:
        return True

    return False


skip_if_offline = pytest.mark.skipif(_offline(), reason="No internet connection")
skip_slow_tests = pytest.mark.skipif(not _run_slow_tests(), reason="Skipping slow tests")


def skip_missing_packages(*names: str) -> callable:
    """Skip a test if any of the specified packages are missing.

    Parameters
    ----------
    names : str
        The names of the packages to check.

    Returns
    -------
    Callable
        A decorator that skips the test if any of the specified packages are missing.
    """

    missing = [f"'{p}'" for p in _missing_packages(*names)]

    if len(missing) == 0:
        return lambda f: f

    if len(missing) == 1:
        return pytest.mark.skipif(True, reason=f"Package {missing[0]} is not installed")

    return pytest.mark.skipif(True, reason=f"Packages {list_to_human(missing)} are not installed")


def skip_if_missing_command(cmd: str) -> callable:
    """Skip a test if the specified command is not available.

    Parameters
    ----------
    cmd : str
        The name of the command to check.

    Returns
    -------
    Callable
        A decorator that skips the test if the specified command is not available.
    """

    import shutil

    if shutil.which(cmd):
        return lambda f: f

    return pytest.mark.skipif(True, reason=f"Command '{cmd}' is not available")


def cli_testing(package: str, cmd: str, *args: list[str]) -> None:
    """Run a CLI command for testing purposes.

    Parameters
    ----------
    package : str
        The name of the package containing the CLI commands.
        Can be 'anemoi-datasets' or 'anemoi.datasets'.
    cmd : str
        The command to run.
    *args : list[str]
        Additional arguments to pass to the command.
    """

    package = package.replace("-", ".")
    COMMANDS = getattr(__import__(f"{package}.commands", fromlist=["COMMANDS"]), "COMMANDS")
    version = getattr(__import__(f"{package}._version", fromlist=["__version__"]), "__version__", "0.1.0")

    from anemoi.utils.cli import cli_main

    cli_main(
        version=version,
        description=f"Testing the '{cmd}' CLI command from the '{package}' package.",
        commands=COMMANDS,
        test_arguments=(cmd,) + args,
    )


def run_tests(globals: dict[str, callable]) -> None:
    """Run all test functions that start with 'test_'.

    Parameters
    ----------
    globals : dict[str, callable]
        The global namespace containing the test functions.

    Example
    -------

    Call from a test file to run all tests in that file:

    ```python
    if __name__ == "__main__":
        from anemoi.utils.testing import run_tests
        run_tests(globals())
    ```

    Useful for debugging or running tests in an interactive environment.

    """
    import logging

    import rich

    logging.basicConfig(level=logging.INFO)

    for name, obj in list(globals.items()):
        if name.startswith("test_") and callable(obj):

            pytestmark = getattr(obj, "pytestmark", None)
            if pytestmark is not None:
                if not isinstance(pytestmark, list):
                    pytestmark = [pytestmark]

                skip = False
                for m in pytestmark:
                    if m.name == "skipif" and m.args == (True,):
                        skip = True
                        rich.print(
                            f"[red]Skipping [bold]{name}[/bold] due to skipif condition [bold]{m.kwargs['reason']}[/bold].[/red]"
                        )
                        break
                if skip:
                    continue

            rich.print(f"[green]Running [bold]{name}[/bold]...[/green]")
            obj()
