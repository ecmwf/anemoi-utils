# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Pydantic models for object storage configuration."""

import warnings
from typing import Literal

from pydantic import Field
from pydantic import SecretStr
from pydantic import field_validator
from pydantic import model_validator

from .base import AnemoiBaseSettingsSchema

# ObjectStorageBucketConfig fields each backend consumes when building clients
_COMMON_CLIENT_FIELDS = frozenset({"endpoint_url", "skip_signature"})
_S3_ONLY_FIELDS = frozenset({"access_key_id", "secret_access_key", "region"})
_AZURE_ONLY_FIELDS = frozenset({"account_name", "account_key", "sas_token"})
S3_CLIENT_FIELDS = _COMMON_CLIENT_FIELDS | _S3_ONLY_FIELDS
AZURE_CLIENT_FIELDS = _COMMON_CLIENT_FIELDS | _AZURE_ONLY_FIELDS


def _reject_mixed_backends(instance: AnemoiBaseSettingsSchema) -> None:
    """Raise if both S3-only and Azure-only fields are set on the same config."""
    s3_set = {f for f in _S3_ONLY_FIELDS if getattr(instance, f, None) is not None}
    az_set = {f for f in _AZURE_ONLY_FIELDS if getattr(instance, f, None) is not None}
    if s3_set and az_set:
        msg = (
            f"Mixed S3 and Azure fields on the same object storage config: S3 fields = {sorted(s3_set)}, Azure fields "
            f"= {sorted(az_set)}. Configure one backend per bucket/account."
        )
        raise ValueError(msg)


class ObjectStorageBucketConfig(AnemoiBaseSettingsSchema):
    """Object storage configuration for S3-compatible and Azure Blob services.

    At the top level (:class:`ObjectStorageConfig`) these fields act as global defaults. Under a named sub-section (e.g.
    `[object-storage."my-bucket"]`) they act as per-bucket/account overrides.
    """

    # common fields
    endpoint_url: str | None = None
    """Endpoint URL. S3-compatible services, Azurite or sovereign clouds for Azure."""
    skip_signature: bool | None = False
    """Skip signature for public storage."""

    # S3 fields
    access_key_id: SecretStr | None = None
    """S3 bucket access key ID."""
    secret_access_key: SecretStr | None = None
    """S3 bucket secret access key."""
    region: str | None = None
    """S3 bucket region."""

    # Azure Blob Storage fields
    account_name: SecretStr | None = None
    """Azure Blob Storage account name."""
    account_key: SecretStr | None = None
    """Azure Blob Storage account key."""
    sas_token: SecretStr | None = None
    """Azure Blob Storage SAS token. May include or omit the leading '?'."""

    @model_validator(mode="after")
    def _no_mixed_backends(self) -> "ObjectStorageBucketConfig":
        _reject_mixed_backends(self)
        return self

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a configuration value with fallback to the global setting."""
        warnings.warn(
            f"{type(self).__name__}.get() is deprecated and will be removed in a future version. Access settings "
            "directly as attributes, rather than viewing this as a dictionary.",
            DeprecationWarning,
            stacklevel=2,
        )
        value = getattr(self, key)
        if value is not None and value != "":
            return value
        return default


class ObjectStorageConfig(ObjectStorageBucketConfig):
    """Top-level, global object storage configuration.

    Inherits all backend fields from :class:`ObjectStorageBucketConfig` used for per-bucket/account overrides under
    `__pydantic_extra__` (named sub-sections, e.g. `[object-storage."my-bucket"]`).
    """

    type: Literal["s3", "az"] | None = None
    """Deprecated: retained for backwards compatibility. Backends are dispatched by URL scheme (`s3://`, `abfs://`)."""

    __pydantic_extra__: dict[str, ObjectStorageBucketConfig] = Field(init=False)  # type: ignore[assignment]

    @field_validator("type", mode="after")
    @classmethod
    def _warn_deprecated_type(cls, value: str | None) -> None:
        if value is not None:
            warnings.warn(
                "The 'type' field on [object-storage] is deprecated and ignored. Backend is chosen by URL scheme "
                "('s3://' or 'abfs://'). Remove it from your settings file.",
                DeprecationWarning,
                stacklevel=2,
            )
