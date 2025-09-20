# (C) Copyright 2025 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import pytest


def test_registry() -> None:
    """Test the Registry class for registering and retrieving factories.

    Tests:
        - Registering factories with and without aliases.
        - Retrieving factories by name and alias.
        - Handling of non-existent factories.
        - Ensuring that warnings are issued for duplicate registrations.
    """
    from anemoi.utils.registry import Registry

    reg = Registry("anemoi.utils", key="name")

    def factory_a():
        return "Factory A"

    def factory_b():
        return "Factory B"

    # Register factories
    reg.register("factory-a", factory_a, source="test_registry", aliases=["fa", "alpha"])
    reg.register("factory-b", factory_b, source="test_registry")

    # Retrieve factories by name
    assert reg.lookup("factory-a") == factory_a
    assert reg.lookup("factory-b") == factory_b

    # Retrieve factories by alias
    assert reg.lookup("fa") == factory_a
    assert reg.lookup("alpha") == factory_a

    # Attempt to retrieve a non-existent factory
    assert reg.lookup("non-existent", return_none=True) is None

    # Call factories
    assert reg.lookup("factory-a")() == "Factory A"
    assert reg.lookup("fa")() == "Factory A"
    assert reg.lookup("factory-b")() == "Factory B"

    # Test duplicate registration warning (this will not raise an error, just a warning)

    with pytest.warns(UserWarning, match="is already registered"):
        reg.register("factory-a", factory_a, source="test_registry_duplicate")

    # Check that using an alias triggers a deprecation warning

    with pytest.warns(DeprecationWarning, match="Alias 'fa' for 'factory-a' in anemoi.utils is deprecated"):
        reg.lookup("fa")


if __name__ == "__main__":
    test_registry()
