# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging
from typing import Any

from ..scheme import Scheme
from . import scheme_registry

LOG = logging.getLogger(__name__)


@scheme_registry.register("checkpoint")
class CheckpointScheme(Scheme):
    """Scheme for handling checkpoint files."""

    def __init__(self, url, refer=None, **kwargs):
        assert False, (url, kwargs)

    def load(self) -> Any:
        """Load the checkpoint file."""
        # Implement the logic to load the checkpoint file
        pass

    def save(self, data: Any) -> None:
        """Save data to the checkpoint file."""
        # Implement the logic to save data to the checkpoint file
        pass
