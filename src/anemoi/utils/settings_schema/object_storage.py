# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import Optional

from pydantic import Field
from pydantic import SecretStr

from .base import AnemoiBaseSettingsSchema


class ObjectStorageBucketConfig(AnemoiBaseSettingsSchema):
    """Per-bucket overrides for object storage configuration."""

    endpoint_url: Optional[str] = None
    """Bucket-specific endpoint URL."""

    access_key_id: Optional[SecretStr] = None
    """Bucket-specific access key ID."""

    secret_access_key: Optional[SecretStr] = None
    """Bucket-specific secret access key."""

    region: Optional[str] = None
    """Bucket-specific region."""

    skip_signature: Optional[bool] = False
    """Skip signature for public buckets."""

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a configuration value with fallback to the global setting."""
        import warnings

        warnings.warn(
            "ObjectStorageBucketConfig.get() is deprecated and will be removed in a future version. "
            "Access bucket-specific settings directly as attributes, rather than viewing this as a dictionary.",
            DeprecationWarning,
            stacklevel=2,
        )
        value = getattr(self, key)
        if value is not None and value != "":
            return value
        return default


class ObjectStorageConfig(AnemoiBaseSettingsSchema):
    """Object storage configuration for S3-compatible services."""

    type: str = "s3"
    """Default storage type (only 's3' is currently supported)."""

    endpoint_url: Optional[str] = None
    """Global endpoint URL (leave empty for default AWS endpoint)."""

    access_key_id: Optional[SecretStr] = None
    """Global access key ID."""

    secret_access_key: Optional[SecretStr] = None
    """Global secret access key."""

    __pydantic_extra__: dict[str, ObjectStorageBucketConfig] = Field(init=False)  # type: ignore[assignment]

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a configuration value with fallback to the global setting."""
        import warnings

        warnings.warn(
            "ObjectStorageConfig.get() is deprecated and will be removed in a future version. "
            "Access settings directly as attributes, rather than viewing this as a dictionary.",
            DeprecationWarning,
            stacklevel=2,
        )
        value = getattr(self, key)
        if value is not None and value != "":
            return value
        return default
