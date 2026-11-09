# (C) Copyright 2024-2026 Anemoi contributors.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
"""Unit tests for Azure Blob Storage remote utilities.

Requires the Azurite blob service running locally, e.g. via `testcontainers` or the VS Code extension.
"""

import os

import pytest

from anemoi.utils.remote import az
from anemoi.utils.testing import skip_missing_packages
from tests.helpers.azurite import AZURITE_ACCOUNT_NAME
from tests.helpers.azurite import AZURITE_BLOB_BODY
from tests.helpers.azurite import AZURITE_BLOB_NAME
from tests.helpers.azurite import AZURITE_BLOB_URL
from tests.helpers.azurite import AZURITE_CONTAINER
from tests.helpers.azurite import AZURITE_ENDPOINT
from tests.helpers.azurite import azurite_reachable

IN_CI = (os.environ.get("GITHUB_WORKFLOW") is not None) or (os.environ.get("IN_CI_HPC") is not None)
pytestmark = [
    pytest.mark.skipif(IN_CI, reason="Test requires access to Azurite not available in CI"),
    skip_missing_packages("obstore"),
    pytest.mark.skipif(not azurite_reachable(), reason=f"Azurite not reachable at endpoint: {AZURITE_ENDPOINT}"),
]


@pytest.mark.parametrize(
    "url",
    [
        AZURITE_BLOB_URL,
        f"abfs://{AZURITE_CONTAINER}@{AZURITE_ACCOUNT_NAME}.blob.core.windows.net/{AZURITE_BLOB_NAME}",
        f"abfs://{AZURITE_CONTAINER}@{AZURITE_ACCOUNT_NAME}.dfs.core.windows.net/{AZURITE_BLOB_NAME}",
        f"abfs://{AZURITE_CONTAINER}@{AZURITE_ACCOUNT_NAME}.dfs.core.windows.net/{AZURITE_BLOB_NAME}?sv=abc123",
    ],
)
def test_assert_azure_url_valid(azurite: None, url: str) -> None:
    """Test detection of supported Azure Blob Storage URLs."""
    az._assert_azure_url(url)  # noqa: SLF001


@pytest.mark.parametrize(
    "url",
    [
        "s3://my-bucket/my-object",
        "https://my-bucket.s3.amazonaws.com/my-object",
        "https://example.com/path/to/resource",
        f"https://{AZURITE_ACCOUNT_NAME}.blob.core.windows.net/{AZURITE_CONTAINER}/{AZURITE_BLOB_NAME}",
    ],
)
def test_assert_azure_url_invalid(azurite: None, url: str) -> None:
    """Test detection of unsupported Azure Blob Storage URLs."""
    with pytest.raises(ValueError, match="Invalid Azure URL:"):
        az._assert_azure_url(url)  # noqa: SLF001


def test_object_exists(azurite: None) -> None:
    """Test existence of objects in Azure Blob Storage."""
    assert az.object_exists(AZURITE_BLOB_URL) is True
    assert az.object_exists("abfs://ml-datasets/does-not-exist") is False


def test_list_folder(azurite: None) -> None:
    """Test listing of objects in Azure Blob Storage."""
    assert len(list(az.list_folder(f"abfs://{AZURITE_CONTAINER}/"))) == 1


def test_object_info(azurite: None) -> None:
    """Test retrieval of metadata for an object in Azure Blob Storage."""
    info = az.object_info(AZURITE_BLOB_URL)
    assert info["path"] == AZURITE_BLOB_NAME


def test_get_object(azurite: None) -> None:
    """Test retrieval of contents for an object in Azure Blob Storage."""
    body = az.get_object(AZURITE_BLOB_URL)
    assert body == AZURITE_BLOB_BODY
