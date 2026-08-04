# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from __future__ import annotations

import base64
import json
import logging
import os
import time
import warnings
from abc import ABC
from abc import abstractmethod
from datetime import datetime
from datetime import timezone
from functools import wraps
from getpass import getpass
from typing import TYPE_CHECKING

import requests
from pydantic import BaseModel
from pydantic import Field
from pydantic import RootModel
from pydantic import field_validator
from pydantic import model_validator
from requests.exceptions import HTTPError

from ..config import CONFIG_LOCK
from ..config import config_path
from ..config import load_raw_config
from ..config import save_config
from ..remote import robust
from ..timer import Timer

REFRESH_EXPIRE_DAYS = 29


if TYPE_CHECKING:
    from collections.abc import Callable


class UserInfo(BaseModel):
    """User info associated with a token."""

    name: str | None = None
    email: str | None = None
    username: str | None = Field(default=None, validation_alias="preferred_username")

    @classmethod
    def from_jwt(cls, token: str) -> "UserInfo":
        """Create a UserInfo object from a JWT. The token payload must contain the user info fields."""
        payload = token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")
        data = json.loads(decoded)
        return cls(**data)

    def __bool__(self) -> bool:
        """A UserInfo object evaluates to True if at least one of its fields is not None."""
        return any(getattr(self, field) is not None for field in UserInfo.model_fields)


class ServerConfig(BaseModel):
    refresh_token: str | None = None
    refresh_expires: int = 0
    static_token: str | None = None

    @field_validator("refresh_expires", mode="before")
    def to_int(cls, value: float | int) -> int:
        if not isinstance(value, int):
            return int(value)
        return value


class ServerStore(RootModel):
    root: dict[str, ServerConfig] = {}

    def get(self, url: str) -> ServerConfig | None:
        return self.root.get(url.rstrip("/"))

    def __getitem__(self, url: str) -> ServerConfig:
        return self.root[url.rstrip("/")]

    def items(self):
        return self.root.items()

    def update(self, url: str, config: ServerConfig) -> None:
        """Update the server configuration for a given URL."""
        self.root[url.rstrip("/")] = config

    @property
    def servers(self) -> list[tuple[str, int]]:
        """List of servers in the store, as a tuple (url, refresh_expires). Ordered most recently used first."""
        return [
            (url, cfg.refresh_expires)
            for url, cfg in sorted(
                self.root.items(),
                key=lambda item: item[1].refresh_expires,
                reverse=True,
            )
        ]

    @model_validator(mode="before")
    @classmethod
    def load_legacy_format(cls, data: dict) -> dict:
        """Convert legacy single-server config format to multi-server."""
        if isinstance(data, dict) and "url" in data:
            _data = data.copy()
            _url = _data.pop("url")
            data = {_url: ServerConfig(**_data)}
        return data

    @model_validator(mode="after")
    def normalise_urls(self) -> ServerStore:
        """Strip trailing slashes for pre-existing store entries."""
        self.root = {url.rstrip("/"): cfg for url, cfg in self.root.items()}
        return self


class AuthBase(ABC):
    """Base class for authentication implementations."""

    _enabled: bool = False

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def save(self, **kwargs):
        pass

    @abstractmethod
    def login(self, force_credentials: bool = False, **kwargs):
        pass

    @abstractmethod
    def authenticate(self, **kwargs):
        pass

    @abstractmethod
    def user_info(self) -> UserInfo:
        pass


class NoAuth(AuthBase):
    """No-op authentication class."""

    def __init__(self, *args, **kwargs):
        self._enabled = False

    def save(self, **kwargs):
        pass

    def login(self, force_credentials: bool = False, **kwargs):
        pass

    def authenticate(self, **kwargs):
        pass

    def user_info(self) -> UserInfo:
        return UserInfo()


def enabled_guard(fn: Callable) -> Callable:
    """Decorator to call or ignore a method based on the instance's `_enabled` flag."""

    @wraps(fn)
    def _wrapper(self: AuthBase, *args, **kwargs) -> Callable | None:
        if self._enabled:
            return fn(self, *args, **kwargs)
        return None

    return _wrapper


class TokenAuth(AuthBase):
    """Manage authentication with a keycloak token server."""

    _config_file = "mlflow-token.json"

    def __init__(
        self,
        url: str | None,
        enabled: bool = True,
        target_env_var: str = "MLFLOW_TRACKING_TOKEN",
    ) -> None:
        """Initialise the token authentication object.

        Parameters
        ----------
        url : str | None
            URL of the authentication server.
        enabled : bool, optional
            Set this to False to turn off authentication, by default True
        target_env_var : str, optional
            The environment variable to store the access token in after authenticating,
            by default `MLFLOW_TRACKING_TOKEN`

        """
        self._refresh_token = None
        self.refresh_expires = 0

        self.access_token: str | None = None
        self.access_expires = 0

        self._enabled = enabled
        self.target_env_var = target_env_var

        # the command line tool adds a default handler to the root logger on runtime,
        # so we init our logger here (on runtime, not on import) to avoid duplicate handlers
        self.log = logging.getLogger(__name__)

        if not url:
            self.url = None
            assert not enabled, "URL must be provided if authentication is enabled."
            return

        self.url = url.rstrip("/")

        store = self._get_store()
        config = store.get(self.url)

        if config is not None:
            self._refresh_token = config.refresh_token
            self.refresh_expires = config.refresh_expires

    def __call__(self) -> None:
        self.authenticate()

    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    @refresh_token.setter
    def refresh_token(self, value: str) -> None:
        self._refresh_token = value
        self.refresh_expires = time.time() + (REFRESH_EXPIRE_DAYS * 86400)  # 86400 seconds in a day

    @staticmethod
    def _get_store() -> ServerStore:
        """Read the server store from disk."""
        with CONFIG_LOCK:
            file = TokenAuth._config_file
            path = config_path(file)

            if not os.path.exists(path):
                save_config(file, {})

            if os.path.exists(path) and os.stat(path).st_mode & 0o777 != 0o600:
                os.chmod(path, 0o600)

            return ServerStore(**load_raw_config(file))

    @staticmethod
    def get_servers() -> list[tuple[str, int]]:
        """List of all saved servers, as a tuple (url, refresh_expires). Ordered most recently used first."""
        return TokenAuth._get_store().servers

    @staticmethod
    def load_config() -> dict:
        """Load the last used server configuration

        Returns
        -------
        config : dict
            Dictionary with the following keys: `url`, `refresh_token`, `refresh_expires`.
            If no configuration is found, an empty dictionary is returned.
        """
        warnings.warn(
            "TokenAuth.load_config() is deprecated and will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2,
        )

        store = TokenAuth._get_store()

        last = {}
        for url, cfg in store.items():
            if cfg.refresh_expires > last.get("refresh_expires", 0):
                # exclude fields added after this deprecated API to preserve its contract
                last = dict(url=url, **cfg.model_dump(exclude={"static_token"}))

        return last

    @enabled_guard
    def login(self, force_credentials: bool = False, **kwargs: dict) -> None:
        """Acquire a new refresh token and save it to disk.

        If an existing valid refresh token is already on disk it will be used.
        If not, or the token has expired, the user will be asked to obtain one from the API.

        Refresh token expiry time is set in the `REFRESH_EXPIRE_DAYS` constant (default 29 days).

        This function should be called once, interactively, right before starting a training run.

        Parameters
        ----------
        force_credentials : bool, optional
            Force a credential login even if a refreh token is available, by default False.
        kwargs : dict
            Additional keyword arguments.

        Raises
        ------
        RuntimeError
            A new refresh token could not be acquired.

        """
        del kwargs  # unused
        self.log.info("🌐 Logging in to %s", self.url)
        new_refresh_token = None

        if not force_credentials and self.refresh_token and self.refresh_expires > time.time():
            new_refresh_token = self._token_request(ignore_exc=True).get("refresh_token")

        if not new_refresh_token:
            self.log.info("📝 Please obtain a seed refresh token from %s/seed", self.url)
            self.log.info("📝 and paste it here (you will not see the output, just press enter after pasting):")
            self.refresh_token = getpass("Refresh Token: ")

            # perform a new refresh token request to check if the seed refresh token is valid
            new_refresh_token = self._token_request().get("refresh_token")

        if not new_refresh_token:
            msg = "❌ Failed to log in. Please try again."
            raise RuntimeError(msg)

        self.refresh_token = new_refresh_token
        self.save()

        self.log.info("✅ Successfully logged in to MLflow. Happy logging!")

    @enabled_guard
    def authenticate(self, **kwargs: dict) -> None:
        """Check the access token and refresh it if necessary. A new refresh token will also be acquired upon refresh.

        This requires a valid refresh token to be available, obtained from the `login` method.

        The access token is stored in memory and in an environment variable.
        If the access token is still valid, this function does nothing.

        This function should be called before every MLflow API request.

        Raises
        ------
        RuntimeError
            No refresh token is available or the token request failed.

        """
        del kwargs  # unused
        if self.access_expires > time.time():
            return

        if not self.refresh_token or self.refresh_expires < time.time():
            msg = "You are not logged in to MLflow. Please log in first."
            raise RuntimeError(msg)

        with Timer("Access token refreshed", self.log):
            response = self._token_request()

        self.access_token = response.get("access_token")
        self.access_expires = time.time() + (response.get("expires_in") * 0.7)  # bit of buffer
        self.refresh_token = response.get("refresh_token")

        os.environ[self.target_env_var] = self.access_token

    @enabled_guard
    def save(self, **kwargs: dict) -> None:
        """Save the latest refresh token to disk."""
        del kwargs  # unused
        if not self.refresh_token:
            self.log.warning("No refresh token to save.")
            return

        server_config = ServerConfig(
            refresh_token=self.refresh_token,
            refresh_expires=self.refresh_expires,
        )

        with CONFIG_LOCK:
            store = self._get_store()
            store.update(self.url, server_config)
            save_config(self._config_file, store.model_dump())

        expire_date = datetime.fromtimestamp(self.refresh_expires, tz=timezone.utc)
        self.log.info(
            "Your MLflow login token is valid until %s UTC",
            expire_date.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def user_info(self) -> UserInfo:
        """Get user info embedded in the access token."""
        self.authenticate()

        if not self.access_token:
            return UserInfo()

        try:
            return UserInfo.from_jwt(self.access_token)
        except Exception as e:
            self.log.exception("Failed to decode access token.", exc_info=e)
            return UserInfo()

    def _token_request(
        self,
        ignore_exc: bool = False,
    ) -> dict:
        path = "refreshtoken"
        payload = {"refresh_token": self.refresh_token}

        try:
            response = self._request(path, payload)
        except Exception:
            if ignore_exc:
                return {}
            raise

        return response

    def _request(self, path: str, payload: dict) -> dict:

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            response = robust(requests.post)(
                f"{self.url}/{path}",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            response_json = response.json()

            if response_json.get("status", "") != "OK":
                error_description = response_json.get("response", "Error acquiring token.")
                msg = f"❌ {error_description}"
                raise RuntimeError(msg)

            return response_json["response"]
        except HTTPError:
            self.log.exception("HTTP error occurred")
            raise


class StaticTokenAuth(AuthBase):
    """Authentication with a static, pre-issued bearer token.

    Unlike `TokenAuth`, this class does not perform any refresh flow or talk to a
    token server. It simply stores the supplied token in the target environment
    variable (by default `MLFLOW_TRACKING_TOKEN`) so that MLflow sends it as an
    `Authorization: Bearer <token>` header on every request.

    The token is persisted to (and loaded from) the same on-disk store used by
    `TokenAuth` (`~/.anemoi/mlflow-token.json`), keyed by server URL. This means a
    token supplied once via `login()` is remembered across sessions, and multiple
    servers can each hold their own static token.

    This is useful for MLflow servers that accept a long-lived HTTP access token.

    Note
    ----
    If the server sits behind a proxy/gateway that enforces per-method
    permissions, the token must allow the HTTP methods the MLflow client uses.
    The client issues several read operations as ``POST``, so a read-only token
    may be insufficient.
    """

    _config_file = TokenAuth._config_file

    def __init__(
        self,
        url: str | None,
        token: str | None = None,
        enabled: bool = True,
        target_env_var: str = "MLFLOW_TRACKING_TOKEN",
    ) -> None:
        """Initialise the static token authentication object.

        Parameters
        ----------
        url : str | None
            URL of the MLflow server the token belongs to. Used as the storage key.
        token : str | None, optional
            The static bearer token to use. If not provided, a previously saved token
            for this URL is loaded from disk. By default None.
        enabled : bool, optional
            Set this to False to turn off authentication, by default True.
        target_env_var : str, optional
            The environment variable to store the access token in,
            by default `MLFLOW_TRACKING_TOKEN`.

        """
        self.access_token = token
        self._enabled = enabled
        self.target_env_var = target_env_var
        self.log = logging.getLogger(__name__)

        if not url:
            self.url = None
            assert not enabled, "URL must be provided if authentication is enabled."
            return

        self.url = url.rstrip("/")

        # load a previously saved token if none was supplied
        if self.access_token is None:
            config = TokenAuth._get_store().get(self.url)
            if config is not None:
                self.access_token = config.static_token

    def __call__(self) -> None:
        self.authenticate()

    @enabled_guard
    def save(self, **kwargs: dict) -> None:
        """Persist the static token to disk, keyed by server URL."""
        del kwargs  # unused
        if not self.access_token:
            self.log.warning("No token to save.")
            return

        with CONFIG_LOCK:
            store = TokenAuth._get_store()
            existing = store.get(self.url)
            config = existing.model_copy() if existing is not None else ServerConfig()
            config.static_token = self.access_token
            store.update(self.url, config)
            save_config(self._config_file, store.model_dump())

    @enabled_guard
    def login(self, force_credentials: bool = False, **kwargs: dict) -> None:
        """Acquire a static token and save it to disk.

        If a token was supplied at construction (or a valid one is already on disk) it
        is reused. Otherwise, or when `force_credentials` is set, the user is prompted
        to paste one interactively.

        Parameters
        ----------
        force_credentials : bool, optional
            Force a prompt for a new token even if one is available, by default False.
        kwargs : dict
            Additional keyword arguments (unused).

        """
        del kwargs  # unused
        self.log.info("🌐 Using static token authentication for %s", self.url)

        if force_credentials or not self.access_token:
            self.log.info("📝 Please paste your MLflow access token")
            self.log.info("📝 (you will not see the output, just press enter after pasting):")
            self.access_token = getpass("Access Token: ")

        if not self.access_token:
            msg = "❌ No token provided. Please try again."
            raise RuntimeError(msg)

        self.save()
        self.authenticate()
        self.log.info("✅ Static token stored. Happy logging!")

    @enabled_guard
    def authenticate(self, **kwargs: dict) -> None:
        """Store the static token in the target environment variable."""
        del kwargs  # unused
        if not self.access_token:
            msg = "You are not logged in to MLflow. Please log in first."
            raise RuntimeError(msg)
        os.environ[self.target_env_var] = self.access_token

    def user_info(self) -> UserInfo:
        """Get user info embedded in the token, if it is a JWT."""
        if not self._enabled or not self.access_token:
            return UserInfo()

        try:
            return UserInfo.from_jwt(self.access_token)
        except Exception as e:
            self.log.exception("Failed to decode access token.", exc_info=e)
            return UserInfo()
