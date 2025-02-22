# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import warnings
from typing import Any
from typing import Callable
from typing import Optional

from .remote import transfer
from .remote.s3 import delete as delete_
from .remote.s3 import s3_client as s3_client_

warnings.warn(
    "The anemoi.utils.s3 module is deprecated and will be removed in a future release. "
    "Please use the 'anemoi.utils.remote' or 'anemoi.utils.remote.s3' module instead.",
    DeprecationWarning,
    stacklevel=2,
)


def s3_client(*args: Any, **kwargs: Any) -> Any:
    """Create an S3 client.

    Parameters
    ----------
    *args : Any
        Positional arguments for the S3 client.
    **kwargs : Any
        Keyword arguments for the S3 client.

    Returns
    -------
    Any
        The S3 client.
    """
    warnings.warn(
        "The 's3_client' function (from anemoi.utils.s3 import s3_client) function is deprecated and will be removed in a future release. "
        "Please use the 's3_client' function (from anemoi.utils.remote.s3 import s3_client) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return s3_client_(*args, **kwargs)


def upload(
    source: str,
    target: str,
    *,
    overwrite: bool = False,
    resume: bool = False,
    verbosity: int = 1,
    progress: Optional[Callable] = None,
    threads: int = 1,
) -> None:
    """Upload a file to S3.

    Parameters
    ----------
    source : str
        The source file path.
    target : str
        The target S3 path.
    overwrite : bool, optional
        Whether to overwrite the target file, by default False.
    resume : bool, optional
        Whether to resume a previous upload, by default False.
    verbosity : int, optional
        The verbosity level, by default 1.
    progress : Callable, optional
        A callback function for progress updates, by default None.
    threads : int, optional
        The number of threads to use, by default 1.
    """
    warnings.warn(
        "The 'upload' function (from anemoi.utils.s3 import upload) function is deprecated and will be removed in a future release. "
        "Please use the 'transfer' function (from anemoi.utils.remote import transfer) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return transfer(
        source, target, overwrite=overwrite, resume=resume, verbosity=verbosity, progress=progress, threads=threads
    )


def download(*args: Any, **kwargs: Any) -> Any:
    """Download a file from S3.

    Parameters
    ----------
    *args : Any
        Positional arguments for the download.
    **kwargs : Any
        Keyword arguments for the download.

    Returns
    -------
    Any
        The result of the download.
    """
    warnings.warn(
        "The 'download' function (from anemoi.utils.s3 import download) function is deprecated and will be removed in a future release. "
        "Please use the 'transfer' function (from anemoi.utils.remote import transfer) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return transfer(*args, **kwargs)


def delete(*args: Any, **kwargs: Any) -> Any:
    """Delete a file from S3.

    Parameters
    ----------
    *args : Any
        Positional arguments for the delete.
    **kwargs : Any
        Keyword arguments for the delete.

    Returns
    -------
    Any
        The result of the delete.
    """
    warnings.warn(
        "The 'delete' function (from anemoi.utils.s3 import delete) function is deprecated and will be removed in a future release. "
        "Please use the 'transfer' function (from anemoi.utils.remote.s3 import delete) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return delete_(*args, **kwargs)
