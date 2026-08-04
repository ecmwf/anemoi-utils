# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import pytest_mock

import anemoi.utils.mlflow.client as client_module
from anemoi.utils.mlflow.client import AnemoiMlflowClient


@pytest.fixture(autouse=True)
def mocks(mocker: pytest_mock.MockerFixture) -> None:
    mocker.patch("anemoi.utils.mlflow.client.TokenAuth")
    mocker.patch("anemoi.utils.mlflow.client.StaticTokenAuth")
    mocker.patch("anemoi.utils.mlflow.client.health_check")
    mocker.patch("anemoi.utils.mlflow.client.AnemoiMlflowClient.search_experiments")


def test_auth_injected() -> None:
    client = AnemoiMlflowClient("http://localhost:5000", authentication=True, check_health=False)
    client.search_experiments()
    client.search_experiments()

    assert client.anemoi_auth.authenticate.call_count == 2


def test_health_check() -> None:
    # the internal health check will trigger an authenticate call
    client = AnemoiMlflowClient("http://localhost:5000", authentication=True, check_health=True)

    client.anemoi_auth.authenticate.assert_called_once()


def test_login_delegates_to_token_auth() -> None:
    client = AnemoiMlflowClient("http://localhost:5000", authentication=True, check_health=False)
    client.login(force_credentials=True)
    client.anemoi_auth.login.assert_called_once_with(force_credentials=True)


def test_uses_token_auth_by_default() -> None:
    AnemoiMlflowClient("http://localhost:5000", authentication=True, check_health=False)
    client_module.TokenAuth.assert_called_once()
    client_module.StaticTokenAuth.assert_not_called()


def test_static_token_string_uses_static_auth() -> None:
    AnemoiMlflowClient(
        "http://localhost:5000",
        authentication=True,
        static_token="my-token",
        check_health=False,
    )
    client_module.StaticTokenAuth.assert_called_once_with("http://localhost:5000", token="my-token", enabled=True)
    client_module.TokenAuth.assert_not_called()


def test_static_token_true_loads_from_disk() -> None:
    AnemoiMlflowClient(
        "http://localhost:5000",
        authentication=True,
        static_token=True,
        check_health=False,
    )
    client_module.StaticTokenAuth.assert_called_once_with("http://localhost:5000", token=None, enabled=True)
    client_module.TokenAuth.assert_not_called()


def test_static_token_false_uses_token_auth() -> None:
    AnemoiMlflowClient(
        "http://localhost:5000",
        authentication=True,
        static_token=False,
        check_health=False,
    )
    client_module.TokenAuth.assert_called_once()
    client_module.StaticTokenAuth.assert_not_called()
