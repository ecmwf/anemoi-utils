# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Read and write extra metadata in PyTorch checkpoints files. These files
are zip archives containing the model weights.
"""

import json
import logging
import os
import time
import zipfile
from tempfile import TemporaryDirectory

import tqdm

LOG = logging.getLogger(__name__)

DEFAULT_NAME = "ai-models.json"
DEFAULT_FOLDER = "anemoi-metadata"


def has_metadata(path: str, name: str = DEFAULT_NAME) -> bool:
    """Check if a checkpoint file has a metadata file

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    name : str, optional
        The name of the metadata file in the zip archive

    Returns
    -------
    bool
        True if the metadata file is found
    """
    with zipfile.ZipFile(path, "r") as f:
        for b in f.namelist():
            if os.path.basename(b) == name:
                return True
    return False


def load_metadata(path: str, name: str = DEFAULT_NAME) -> dict:
    """Load metadata from a checkpoint file

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    name : str, optional
        The name of the metadata file in the zip archive

    Returns
    -------
    dict
        The content of the metadata file from JSON

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
                    raise ValueError(f"Found two or more '{name}' in {path}.")
                metadata = b

    if metadata is not None:
        with zipfile.ZipFile(path, "r") as f:
            return json.load(f.open(metadata, "r"))
    else:
        raise ValueError(f"Could not find '{name}' in {path}.")


def save_metadata(path, metadata, name=DEFAULT_NAME, folder=DEFAULT_FOLDER) -> None:
    """Save metadata to a checkpoint file

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    metadata : JSON
        A JSON serializable object
    name : str, optional
        The name of the metadata file in the zip archive
    folder : str, optional
        The folder where the metadata file will be saved
    """
    with zipfile.ZipFile(path, "a") as zipf:

        directories = set()

        for b in zipf.namelist():
            directory = os.path.dirname(b)
            while os.path.dirname(directory) not in (".", ""):
                directory = os.path.dirname(directory)
            directories.add(directory)

            if os.path.basename(b) == name:
                raise ValueError(f"'{name}' already in {path}")

        if len(directories) != 1:
            # PyTorch checkpoints should have a single directory
            # otherwise PyTorch will complain
            raise ValueError(f"No or multiple directories in the checkpoint {path}, directories={directories}")

        directory = list(directories)[0]

        LOG.info("Saving metadata to %s/%s/%s", directory, folder, name)

        zipf.writestr(
            f"{directory}/{folder}/{name}",
            json.dumps(metadata),
        )


def _edit_metadata(path, name, callback):
    new_path = f"{path}.anemoi-edit-{time.time()}-{os.getpid()}.tmp"

    found = False

    with TemporaryDirectory() as temp_dir:
        zipfile.ZipFile(path, "r").extractall(temp_dir)
        total = 0
        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                total += 1
                full = os.path.join(root, f)
                if f == name:
                    found = True
                    callback(full)

        if not found:
            raise ValueError(f"Could not find '{name}' in {path}")

        with zipfile.ZipFile(new_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            with tqdm.tqdm(total=total, desc="Rebuilding checkpoint") as pbar:
                for root, dirs, files in os.walk(temp_dir):
                    for f in files:
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, temp_dir)
                        zipf.write(full, rel)
                        pbar.update(1)

    os.rename(new_path, path)
    LOG.info("Updated metadata in %s", path)


def replace_metadata(path, metadata, name=DEFAULT_NAME):

    if not isinstance(metadata, dict):
        raise ValueError(f"metadata must be a dict, got {type(metadata)}")

    if "version" not in metadata:
        raise ValueError("metadata must have a 'version' key")

    def callback(full):
        with open(full, "w") as f:
            json.dump(metadata, f)

    _edit_metadata(path, name, callback)


def remove_metadata(path, name=DEFAULT_NAME):

    LOG.info("Removing metadata '%s' from %s", name, path)

    def callback(full):
        os.remove(full)

    _edit_metadata(path, name, callback)
