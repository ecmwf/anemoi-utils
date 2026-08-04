# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import json
import sys
import tempfile
from pathlib import Path

import pytest

from anemoi.utils import provenance


@pytest.fixture(autouse=True)
def clear_cache():
    provenance.editable_installs.cache_clear()
    yield


def test_gather() -> None:
    """Test success of gather_provenance_info."""
    provenance.gather_provenance_info()


def test_get_package_source_url_with_git_integration():
    """Test _get_package_source_url on a synthetic .dist-info structure.

    Create a temporary package metadata directory that Python's importlib.metadata
    can read
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # This is what pip creates when installing a package
        dist_info = Path(tmpdir) / "test_git_package-1.0.0.dist-info"
        dist_info.mkdir()

        # Create METADATA file (required for importlib.metadata to recognize it)
        metadata_content = """Metadata-Version: 2.1
Name: test-git-package
Version: 1.0.0
"""
        (dist_info / "METADATA").write_text(metadata_content)

        # Create direct_url.json - this is what pip creates for git installs
        direct_url_content = {
            "url": "git+https://github.com/ways/anemoi-core.git@models-0.12.0",
            "vcs_info": {
                "commit_id": "abc123def456",
                "requested_revision": "models-0.12.0",
                "vcs": "git",
            },
            "subdirectory": "models",
        }
        (dist_info / "direct_url.json").write_text(json.dumps(direct_url_content))

        # Add tmpdir to sys.path so importlib.metadata can discover it
        sys.path.insert(0, tmpdir)

        try:
            result = provenance._get_package_source_url("test-git-package")

            assert result is not None, "Should return source info for git package"
            assert result["url"] == "git+https://github.com/ways/anemoi-core.git@models-0.12.0"
            assert result["vcs_info"]["commit_id"] == "abc123def456"
            assert result["vcs_info"]["requested_revision"] == "models-0.12.0"
            assert result["subdirectory"] == "models"

        finally:
            # Clean up
            sys.path.remove(tmpdir)


def test_get_package_source_url_regular_package_integration():
    """Test with a real regular package installed from PyPI."""
    # pip is always installed and almost always from PyPI, not git
    result = provenance._get_package_source_url("pip")

    # For a regular PyPI package, should return None (no direct_url.json)
    # In rare dev environments pip might be from git, but that's also valid
    assert result is None or isinstance(result, dict)


def test_get_package_source_url_nonexistent():
    """Test with a package that doesn't exist."""
    result = provenance._get_package_source_url("nonexistent-package-xyz-12345")
    assert result is None


def test_is_editable_install_with_editable_package():
    """Test is_editable_install() with a synthetic editable package."""
    with tempfile.TemporaryDirectory() as tmpdir:
        site_packages = Path(tmpdir) / "site-packages"
        site_packages.mkdir()

        # Create the source directory (what direct_url.json points to)
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        # Create dist-info for the editable package
        dist_info = site_packages / "my_editable_package-1.0.0.dist-info"
        dist_info.mkdir()

        (dist_info / "METADATA").write_text("Metadata-Version: 2.1\nName: my-editable-package\nVersion: 1.0.0\n")

        # direct_url.json points to the source directory
        direct_url_content = {
            "url": f"file://{src_dir}",
            "dir_info": {"editable": True},
        }
        (dist_info / "direct_url.json").write_text(json.dumps(direct_url_content))
        (dist_info / "top_level.txt").write_text("my_editable_package\n")

        # The actual package lives in the source directory, not site-packages
        package_dir = src_dir / "my_editable_package"
        package_dir.mkdir()
        init_file = package_dir / "__init__.py"
        init_file.write_text("# Test package")

        sys.path.insert(0, str(site_packages))
        try:
            result = provenance.is_editable_install(str(init_file))
            assert result is True, "Should detect editable install"
        finally:
            sys.path.remove(str(site_packages))


def test_is_editable_install_with_regular_package():
    """Test is_editable_install() with a regular (non-editable) package.

    Create a temporary package metadata directory that simulates a regular install.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fake site-packages directory
        site_packages = Path(tmpdir) / "site-packages"
        site_packages.mkdir()

        # Create a fake package directory
        package_dir = site_packages / "my_regular_package"
        package_dir.mkdir(parents=True)
        init_file = package_dir / "__init__.py"
        init_file.write_text("# Test package")

        # Create dist-info for the regular package
        dist_info = site_packages / "my_regular_package-1.0.0.dist-info"
        dist_info.mkdir()

        # Create METADATA file
        metadata_content = """Metadata-Version: 2.1
Name: my-regular-package
Version: 1.0.0
"""
        (dist_info / "METADATA").write_text(metadata_content)

        # Regular packages don't have direct_url.json or have it without editable flag
        # We'll test without direct_url.json (typical PyPI install)

        # Create top_level.txt
        (dist_info / "top_level.txt").write_text("my_regular_package\n")

        # Add site-packages to sys.path so importlib.metadata can discover it
        sys.path.insert(0, str(site_packages))

        try:
            result = provenance.is_editable_install(str(init_file))
            assert result is False, "Should not detect regular install as editable"
        finally:
            # Clean up
            sys.path.remove(str(site_packages))


def test_is_editable_install_with_non_editable_direct_url():
    """Test is_editable_install() with a package installed from git but not editable.

    This simulates `pip install git+https://...` without -e flag.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fake site-packages directory
        site_packages = Path(tmpdir) / "site-packages"
        site_packages.mkdir()

        # Create a fake package directory
        package_dir = site_packages / "my_git_package"
        package_dir.mkdir(parents=True)
        init_file = package_dir / "__init__.py"
        init_file.write_text("# Test package")

        # Create dist-info for the git package
        dist_info = site_packages / "my_git_package-1.0.0.dist-info"
        dist_info.mkdir()

        # Create METADATA file
        metadata_content = """Metadata-Version: 2.1
Name: my-git-package
Version: 1.0.0
"""
        (dist_info / "METADATA").write_text(metadata_content)

        # Create direct_url.json without editable flag (git install but not editable)
        direct_url_content = {
            "url": "git+https://github.com/example/repo.git",
            "vcs_info": {
                "commit_id": "abc123",
                "vcs": "git",
            },
        }
        (dist_info / "direct_url.json").write_text(json.dumps(direct_url_content))

        # Create top_level.txt
        (dist_info / "top_level.txt").write_text("my_git_package\n")

        # Add site-packages to sys.path so importlib.metadata can discover it
        sys.path.insert(0, str(site_packages))

        try:
            result = provenance.is_editable_install(str(init_file))
            assert result is False, "Should not detect git install without -e as editable"
        finally:
            # Clean up
            sys.path.remove(str(site_packages))


def test_is_editable_install_with_nonexistent_path():
    """Test is_editable_install() with a path that doesn't exist."""
    result = provenance.is_editable_install("/nonexistent/path/to/__init__.py")
    assert result is False, "Should return False for nonexistent path"


def test_lookup_git_repo_with_non_editable_package(mocker):
    """Test that lookup_git_repo() returns None for non-editable packages.

    This is the key behavior change - git repo lookup should only work for
    editable installs.
    """
    # Mock is_editable_install to return False
    mocker.patch("anemoi.utils.provenance.is_editable_install", return_value=False)

    # Even if there's a git repo, it should return None for non-editable packages
    result = provenance.lookup_git_repo("/some/path/to/package/__init__.py")

    assert result is None, "Should return None for non-editable packages"


def test_lookup_git_repo_with_editable_package_no_git(mocker):
    """Test that lookup_git_repo() returns None for editable packages without git."""
    # Mock is_editable_install to return True
    mocker.patch("anemoi.utils.provenance.is_editable_install", return_value=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fake package file (not in a git repo)
        test_file = Path(tmpdir) / "test_package" / "__init__.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("# Test")

        result = provenance.lookup_git_repo(str(test_file))

        assert result is None, "Should return None when no git repo is found"


def test_lookup_git_repo_without_gitpython(mocker):
    """Test that lookup_git_repo() returns None when GitPython is not available."""
    # Mock the import to raise ImportError
    import builtins

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "git":
            raise ImportError("No module named 'git'")
        return original_import(name, *args, **kwargs)

    mocker.patch("builtins.__import__", side_effect=mock_import)

    result = provenance.lookup_git_repo("/some/path")

    assert result is None, "Should return None when GitPython is not available"
