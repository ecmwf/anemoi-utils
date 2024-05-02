# (C) Copyright 2024 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Read and write extra metadata in PyTorch checkpoints files. These files
are zip archives containing the model weights.
"""

import json
import logging
import os
import zipfile

LOG = logging.getLogger(__name__)

DEFAULT_NAME = "anemoi-metadata.json"


def load_metadata(path: str, name: str = DEFAULT_NAME):
    """Load metadata from a checkpoint file

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    name : str, optional
        The name of the metadata file in the zip archive

    Returns
    -------
    JSON
        The content of the metadata file

    Raises
    ------
    ValueError
        If the metadata file is not found
    """
    with zipfile.ZipFile(path, "r") as f:
        metadata = None
        for b in f.namelist():
            if os.path.basename(b) == name:
                if metadata is not None:
                    LOG.warning(f"Found two '{name}' if {path}")
                metadata = b

    if metadata is not None:
        with zipfile.ZipFile(path, "r") as f:
            return json.load(f.open(metadata, "r"))
    else:
        raise ValueError(f"Could not find {name} in {path}")


def save_metadata(path, metadata, name=DEFAULT_NAME):
    """Save metadata to a checkpoint file

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    metadata : JSON
        A JSON serializable object
    name : str, optional
        The name of the metadata file in the zip archive
    """
    with zipfile.ZipFile(path, "a") as zipf:
        base, _ = os.path.splitext(os.path.basename(path))
        zipf.writestr(
            f"{base}/{name}",
            json.dumps(metadata),
        )
