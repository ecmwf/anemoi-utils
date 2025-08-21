# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import annotations

import os
import time

import pytest

from anemoi.utils.mlflow.auth import NoAuth
from anemoi.utils.mlflow.auth import ServerStore
from anemoi.utils.mlflow.auth import TokenAuth


def mocks(
    mocker: pytest.MockerFixture,
    token_request: dict | None = None,
    load_config: dict | None = None,
) -> pytest.Mock:
    if load_config is None:
        load_config = {}
    if token_request is None:
        token_request = {}
    response = {
        "access_token": "access_token",
        "expires_in": 3600,
        "refresh_token": "new_refresh_token",
    }
    response.update(token_request)

    config = {
        "https://test.url": {
            "refresh_token": "old_refresh_token",
            "refresh_expires": time.time() + 3600,
        }
    }
    config["https://test.url"].update(load_config)

    mock_token_request = mocker.patch(
        "anemoi.utils.mlflow.auth.TokenAuth._token_request",
        return_value=response,
    )
    mocker.patch(
        "anemoi.utils.mlflow.auth.load_raw_config",
        return_value=config,
    )
    mocker.patch(
        "anemoi.utils.mlflow.auth.save_config",
    )
    mocker.patch(
        "anemoi.utils.mlflow.auth.getpass",
        return_value="seed_refresh_token",
    )
    mocker.patch("os.environ")

    return mock_token_request


def test_auth(mocker: pytest.MockerFixture) -> None:
    mock_token_request = mocks(mocker)

    auth = TokenAuth("https://test.url")

    assert auth.access_token is None
    assert auth.refresh_token == "old_refresh_token"  # noqa: S105

    auth.authenticate()
    # test that no new token is requested the second time
    auth.authenticate()

    mock_token_request.assert_called_once()

    assert auth.access_token == "access_token"  # noqa: S105
    assert auth.access_expires > time.time()
    assert auth.refresh_token == "new_refresh_token"  # noqa: S105


def test_not_logged_in(mocker: pytest.MockerFixture) -> None:
    # no refresh token
    mocks(mocker, load_config={"refresh_token": None})
    auth = TokenAuth("https://test.url")
    pytest.raises(RuntimeError, auth.authenticate)

    # expired refresh token
    mocks(mocker, load_config={"refresh_expires": time.time() - 1})
    auth = TokenAuth("https://test.url")
    pytest.raises(RuntimeError, auth.authenticate)


def test_login(mocker: pytest.MockerFixture) -> None:
    # normal login
    mock_token_request = mocks(mocker)
    auth = TokenAuth("https://test.url")
    auth.login()

    mock_token_request.assert_called_once()

    # normal credential login
    mock_token_request = mocks(mocker, load_config={"refresh_token": None})
    auth = TokenAuth("https://test.url")
    auth.login()

    mock_token_request.assert_called_once()

    # forced credential login
    mock_token_request = mocks(mocker)
    auth = TokenAuth("https://test.url")
    auth.login(force_credentials=True)

    mock_token_request.assert_called_once()

    # failed login
    mock_token_request = mocks(mocker, token_request={"refresh_token": None})
    auth = TokenAuth("https://test.url")
    pytest.raises(RuntimeError, auth.login)

    assert mock_token_request.call_count == 2


def test_enabled(mocker: pytest.MockerFixture) -> None:
    mock_token_request = mocks(mocker)
    auth = TokenAuth("https://test.url", enabled=False)
    auth.authenticate()

    mock_token_request.assert_not_called()


def test_api(mocker: pytest.MockerFixture) -> None:
    mocks(mocker)
    auth = TokenAuth("https://test.url")
    mock_post = mocker.patch("requests.post")

    # successful request
    response_json = {"status": "OK", "response": {}}
    mocker.patch("requests.post.return_value.json", return_value=response_json)
    response = auth._request("path", {"key": "value"})

    assert response == response_json["response"]
    mock_post.assert_called_once_with(
        "https://test.url/path",
        json={"key": "value"},
        headers=mocker.ANY,
        timeout=mocker.ANY,
    )

    # api error
    error_response = {"status": "ERROR", "response": {}}
    mocker.patch("requests.post.return_value.json", return_value=error_response)

    with pytest.raises(RuntimeError):
        auth._request("path", {"key": "value"})


def test_target_env_var(mocker: pytest.MockerFixture) -> None:
    mocks(mocker)
    auth = TokenAuth("https://test.url", target_env_var="MLFLOW_TEST_ENV_VAR")
    auth.authenticate()

    os.environ.__setitem__.assert_called_once_with("MLFLOW_TEST_ENV_VAR", "access_token")


def test_noauth_init():
    """Test NoAuth can be initialized without error."""
    auth = NoAuth()
    assert isinstance(auth, NoAuth)
    assert hasattr(auth, "_enabled")
    assert auth._enabled is False


def test_noauth_methods_do_nothing():
    """Test NoAuth methods do nothing and return None."""
    auth = NoAuth()
    assert auth.save() is None
    assert auth.login() is None
    assert auth.authenticate() is None


def test_config_format(mocker: pytest.MockerFixture) -> None:
    mocks(mocker)

    legacy_config = {
        "url": "https://test.url",
        "refresh_token": "some_refresh_token",
        "refresh_expires": 123,
    }
    new_config = {
        legacy_config["url"]: {
            "refresh_token": legacy_config["refresh_token"],
            "refresh_expires": legacy_config["refresh_expires"],
        }
    }
    mocker.patch(
        "anemoi.utils.mlflow.auth.load_raw_config",
        return_value=legacy_config,
    )

    config = TokenAuth.load_config(url="https://test.url")
    # the public interface of load_config has not changed, it still returns a dict identical to the legacy format
    assert config == legacy_config

    # test that the store can handle both formats and the outputs are identical
    legacy_store = ServerStore(legacy_config)
    new_store = ServerStore(new_config)
    assert legacy_store["https://test.url"].model_dump() == new_store["https://test.url"].model_dump() == legacy_config
    assert legacy_store.model_dump() == new_store.model_dump() == new_config


@pytest.mark.parametrize(
    "url, unknown",
    [
        (None, False),
        ("https://server-1.url", False),
        ("https://server-2.url", False),
        ("https://server-3.url", False),
        ("https://unknown.url", True),
    ],
)
def test_multi_server_load_config(mocker: pytest.MockerFixture, url: str, unknown: bool) -> None:
    mocks(mocker)

    multi_config = {
        "https://server-1.url": {
            "refresh_token": "refresh-token-1",
            "refresh_expires": 1,
        },
        "https://server-3.url": {
            "refresh_token": "refresh-token-3",
            "refresh_expires": 3,
        },
        "https://server-2.url": {
            "refresh_token": "refresh-token-2",
            "refresh_expires": 2,
        },
    }
    mocker.patch(
        "anemoi.utils.mlflow.auth.load_raw_config",
        return_value=multi_config,
    )

    config = TokenAuth.load_config(url=url)

    if url is None:
        url = "https://server-3.url"  # the last used server (highest expiry time) is returned if no URL is specified

    if unknown:
        assert config == {}
    else:
        assert config == dict(url=url, **multi_config[url])
