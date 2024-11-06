# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import warnings

from .remote import transfer
from .remote.s3 import delete as delete_
from .remote.s3 import s3_client as s3_client_

warnings.warn(
    "The anemoi.utils.s3 module is deprecated and will be removed in a future release. "
    "Please use the 'anemoi.utils.remote' or 'anemoi.utils.remote.s3' module instead.",
    DeprecationWarning,
    stacklevel=2,
)


def s3_client(*args, **kwargs):
    warnings.warn(
        "The 's3_client' function (from anemoi.utils.s3 import s3_client) function is deprecated and will be removed in a future release. "
        "Please use the 's3_client' function (from anemoi.utils.remote.s3 import s3_client) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return s3_client_(*args, **kwargs)


def upload(source, target, *, overwrite=False, resume=False, verbosity=1, progress=None, threads=1) -> None:
    warnings.warn(
        "The 'upload' function (from anemoi.utils.s3 import upload) function is deprecated and will be removed in a future release. "
        "Please use the 'transfer' function (from anemoi.utils.remote import transfer) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return transfer(
        source, target, overwrite=overwrite, resume=resume, verbosity=verbosity, progress=progress, threads=threads
    )


def download(*args, **kwargs):
    warnings.warn(
        "The 'download' function (from anemoi.utils.s3 import download) function is deprecated and will be removed in a future release. "
        "Please use the 'transfer' function (from anemoi.utils.remote import transfer) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return transfer(*args, **kwargs)


def delete(*args, **kwargs):
    warnings.warn(
        "The 'delete' function (from anemoi.utils.s3 import delete) function is deprecated and will be removed in a future release. "
        "Please use the 'transfer' function (from anemoi.utils.remote.s3 import delete) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return delete_(*args, **kwargs)
