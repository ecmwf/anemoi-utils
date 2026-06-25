# (C) Copyright 2024 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import logging
from typing import Any
from urllib.parse import urlparse

from anemoi.utils.registry import Registry

LOG = logging.getLogger(__name__)
scheme_registry = Registry(__name__)


def create_scheme(url: str, refer=None, **kwargs) -> Any:
    parsed = urlparse(url)
    LOG.info(f"Creating scheme from {parsed=} with {kwargs}")
    return scheme_registry.from_config({"_type": parsed.scheme}, url, refer=refer, **kwargs)
