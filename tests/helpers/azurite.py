# (C) Copyright 2024-2026 Anemoi contributors.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Helper functionality for testing with Azurite (Azure Blob Storage emulator)."""

import base64
import hashlib
import hmac
import os
import socket
import uuid
from datetime import UTC
from datetime import datetime
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request
from urllib.request import urlopen

# Azurite defaults
AZURITE_ENDPOINT = os.environ.get("AZURITE_BLOB_ENDPOINT", "http://127.0.0.1:10000/")
AZURITE_ACCOUNT_NAME = os.environ.get("AZURITE_ACCOUNT_NAME", "devstoreaccount1")
AZURITE_ACCOUNT_KEY = os.environ.get(
    "AZURITE_ACCOUNT_KEY",
    "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==",
)
AZURITE_API_VERSION = "2023-11-03"
AZURITE_CONTAINER = "anemoi-utils-tests"
AZURITE_BLOB_NAME = f"test-{uuid.uuid4()}.txt"
AZURITE_BLOB_URL = f"abfs://{AZURITE_CONTAINER}/{AZURITE_BLOB_NAME}"
AZURITE_BLOB_BODY = b"anemoi-utils test blob for Azure Blob Storage unit tests."


def azurite_reachable() -> bool:
    """Return True if Azurite is reachable at the configured endpoint."""
    u = urlparse(AZURITE_ENDPOINT)
    try:
        with socket.create_connection((u.hostname, u.port or 10000), timeout=0.5):
            return True
    except OSError:
        return False


def create_container(name: str) -> None:
    """Create a container on Azurite using the REST API and Shared Key auth.

    Cannot be done with `obstore` and mitigates extra dependencies like `azure-storage-blob`.

    Ignores HTTP 409 (already exists).
    See https://learn.microsoft.com/rest/api/storageservices/create-container
    """
    date = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
    canon_headers = f"x-ms-date:{date}\nx-ms-version:{AZURITE_API_VERSION}\n"
    canon_resource = f"/{AZURITE_ACCOUNT_NAME}/{AZURITE_ACCOUNT_NAME}/{name}\nrestype:container"
    string_to_sign = "\n".join(["PUT", *([""] * 11)]) + "\n" + canon_headers + canon_resource
    key = base64.b64decode(AZURITE_ACCOUNT_KEY)
    signature = base64.b64encode(hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha256).digest()).decode()

    url = f"{AZURITE_ENDPOINT.rstrip('/')}/{AZURITE_ACCOUNT_NAME}/{name}?restype=container"
    req = Request(  # noqa: S310
        url,
        method="PUT",
        headers={
            "x-ms-date": date,
            "x-ms-version": AZURITE_API_VERSION,
            "Authorization": f"SharedKey {AZURITE_ACCOUNT_NAME}:{signature}",
            "Content-Length": "0",
        },
    )
    exists_code = 409
    created_code = 201
    url_return = None
    try:
        url_return = urlopen(req, timeout=5)  # noqa: S310
    except HTTPError as e:
        if e.code != exists_code:
            raise
    if url_return is not None and url_return.status != created_code:
        msg = f"Failed to create container {name} on Azurite: {url_return.status} {url_return.reason}"
        raise RuntimeError(msg)
