# (C) Copyright 2024-2026 Anemoi contributors.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import contextlib
from collections.abc import Generator
from functools import partial

import pytest
from pydantic import SecretStr

from anemoi.utils.remote import az
from anemoi.utils.settings import SETTINGS
from anemoi.utils.settings_schema.object_storage import ObjectStorageConfig
from tests.helpers.azurite import AZURITE_ACCOUNT_KEY
from tests.helpers.azurite import AZURITE_ACCOUNT_NAME
from tests.helpers.azurite import AZURITE_BLOB_BODY
from tests.helpers.azurite import AZURITE_BLOB_NAME
from tests.helpers.azurite import AZURITE_CONTAINER
from tests.helpers.azurite import AZURITE_ENDPOINT
from tests.helpers.azurite import create_container


@pytest.fixture(scope="session")
def azurite() -> Generator[None]:
    """Test session-scoped fixture to set up Azurite and anemoi configuration for testing.

    Seeds a known blob for testing existence, listing and metadata retrieval.
    """
    import obstore  # noqa: PLC0415

    create_container(AZURITE_CONTAINER)

    # patch from_url in test and anemoi.utils.remote.az to allow http for Azurite
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(obstore.store, "from_url", partial(obstore.store.from_url, client_options={"allow_http": True}))
        original = SETTINGS.object_storage
        SETTINGS.object_storage = ObjectStorageConfig(
            account_name=SecretStr(AZURITE_ACCOUNT_NAME),
            account_key=SecretStr(AZURITE_ACCOUNT_KEY),
            endpoint_url=f"{AZURITE_ENDPOINT.rstrip('/')}/{AZURITE_ACCOUNT_NAME}",
        )
        az.CLIENT_CACHE.clear()
        store = None
        try:
            store = obstore.store.from_url(
                f"abfs://{AZURITE_CONTAINER}",
                account_name=AZURITE_ACCOUNT_NAME,
                account_key=AZURITE_ACCOUNT_KEY,
                endpoint=f"{AZURITE_ENDPOINT.rstrip('/')}/{AZURITE_ACCOUNT_NAME}",
            )
            obstore.put(store, AZURITE_BLOB_NAME, AZURITE_BLOB_BODY)
            yield
        finally:
            if store is not None:
                with contextlib.suppress(Exception):
                    obstore.delete(store, AZURITE_BLOB_NAME)
            SETTINGS.object_storage = original
            az.CLIENT_CACHE.clear()
