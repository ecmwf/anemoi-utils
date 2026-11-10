# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
from __future__ import annotations

import os

import requests

from ..remote import robust


def health_check(tracking_uri: str) -> None:
    """Query the health endpoint of an MLflow server.

    If the server is not reachable, raise an error and remind the user that authentication may be required.

    Raises
    ------
    ConnectionError
        If the server is not reachable.

    """
    username = os.getenv("MLFLOW_TRACKING_USERNAME")
    password = os.getenv("MLFLOW_TRACKING_PASSWORD")
    token = os.getenv("MLFLOW_TRACKING_TOKEN")

    # Authenticate health probe the same way the MLflow client does: HTTP basic auth
    # when MLFLOW_TRACKING_USERNAME / MLFLOW_TRACKING_PASSWORD are set, otherwise bearer token.
    request_kwargs: dict = {"timeout": 60}
    if username and password:
        request_kwargs["auth"] = (username, password)
    elif token:
        request_kwargs["headers"] = {"Authorization": f"Bearer {token}"}

    response = robust(requests.get, retry_after=30, maximum_tries=10)(
        f"{tracking_uri}/health",
        **request_kwargs,
    )

    # response.text might vary between MLflow deployments, use status code.
    if response.ok:
        return

    error_msg = f"Could not connect to MLflow server at {tracking_uri}. "
    if not (token or (username and password)):
        error_msg += "The server may require authentication, did you forget to turn it on?"
    raise ConnectionError(error_msg)
