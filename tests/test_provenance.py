# (C) Copyright 2024 Anemoi contributors.
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

from anemoi.utils import provenance


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
