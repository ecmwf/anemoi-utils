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
from collections.abc import Callable
from tempfile import TemporaryDirectory

import tqdm

LOG = logging.getLogger(__name__)

DEFAULT_NAME = "ai-models.json"
DEFAULT_FOLDER = "anemoi-metadata"


def has_metadata(path: str, *, name: str = DEFAULT_NAME) -> bool:
    """Check if a checkpoint file has a metadata file.

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


def metadata_root(path: str, *, name: str = DEFAULT_NAME) -> str:
    """Get the root directory of the metadata file.

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    name : str, optional
        The name of the metadata file in the zip archive

    Returns
    -------
    str
        The root directory of the metadata file

    Raises
    ------
    ValueError
        If the metadata file is not found
    """
    with zipfile.ZipFile(path, "r") as f:
        for b in f.namelist():
            if os.path.basename(b) == name:
                return os.path.dirname(b)
    raise ValueError(f"Could not find '{name}' in {path}.")


def load_metadata(path: str, *, supporting_arrays: bool = False, name: str = DEFAULT_NAME) -> dict:
    """Load metadata from a checkpoint file.

    Parameters
    ----------
    path : str
        The path to the checkpoint file

    supporting_arrays : bool, optional
        If True, the function will return a dictionary with the supporting arrays

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
            metadata = json.load(f.open(metadata, "r"))
            if supporting_arrays:
                arrays = load_supporting_arrays(f, metadata.get("supporting_arrays_paths", {}))
                return metadata, arrays

            return metadata
    else:
        raise ValueError(f"Could not find '{name}' in {path}.")


def load_supporting_arrays(zipf: zipfile.ZipFile, entries: dict) -> dict:
    """Load supporting arrays from a zip file.

    Parameters
    ----------
    zipf : zipfile.ZipFile
        The zip file
    entries : dict
        A dictionary of entries with paths, shapes, and dtypes

    Returns
    -------
    dict
        A dictionary of supporting arrays
    """
    import numpy as np

    supporting_arrays = {}
    for key, entry in entries.items():
        supporting_arrays[key] = np.frombuffer(
            zipf.read(entry["path"]),
            dtype=entry["dtype"],
        ).reshape(entry["shape"])
    return supporting_arrays


def save_metadata(
    path: str, metadata: dict, *, supporting_arrays: dict = None, name: str = DEFAULT_NAME, folder: str = DEFAULT_FOLDER
) -> None:
    """Save metadata to a checkpoint file.

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    metadata : dict
        A JSON serializable object
    supporting_arrays : dict, optional
        A dictionary of supporting NumPy arrays
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

        LOG.info("Adding extra information to checkpoint %s", path)
        LOG.info("Saving metadata to %s/%s/%s", directory, folder, name)

        metadata = metadata.copy()

        def create_supporting_array_entry(key: str, value) -> dict:
            return dict(path=f"{directory}/{folder}/{key}.numpy", shape=value.shape, dtype=str(value.dtype))

        metadata["supporting_arrays_paths"] = supporting_arrays_ = {}
        if supporting_arrays is not None:
            for key, value in supporting_arrays.items():
                if isinstance(value, dict):
                    supporting_arrays_[key] = {}
                    for subkey, subvalue in value.items():
                        supporting_arrays_[key][subkey] = create_supporting_array_entry(f"{key}/{subkey}", subvalue)
                else:
                    supporting_arrays_[key] = create_supporting_array_entry(key, value)

        zipf.writestr(f"{directory}/{folder}/{name}", json.dumps(metadata))

        def save_supporting_array(name: str, entry: dict, value) -> None:
            LOG.info(
                "Saving supporting array `%s` to %s (shape=%s, dtype=%s)",
                name,
                entry["path"],
                entry["shape"],
                entry["dtype"],
            )
            zipf.writestr(entry["path"], value.tobytes())

        for name, entry in metadata["supporting_arrays_paths"].items():
            if isinstance(entry, dict):
                for subname, subentry in entry.items():
                    subvalue = supporting_arrays[name][subname]
                    save_supporting_array(f"{name}/{subname}", subentry, subvalue)
            else:
                value = supporting_arrays[name]
                save_supporting_array(name, entry, value)


def _edit_metadata(path: str, name: str, callback: Callable, supporting_arrays: dict | None = None) -> None:
    """Edit metadata in a checkpoint file.

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    name : str
        The name of the metadata file in the zip archive
    callback : Callable
        A callback function to edit the metadata
    supporting_arrays : dict, optional
        A dictionary of supporting NumPy arrays
    """
    new_path = f"{path}.anemoi-edit-{time.time()}-{os.getpid()}.tmp"

    with zipfile.ZipFile(path, "r") as source_zip:
        file_list = source_zip.namelist()

        # Find the target file and its directory
        target_file = None
        directory = None
        for file_path in file_list:
            if os.path.basename(file_path) == name:
                target_file = file_path
                directory = os.path.dirname(file_path)
                break

        if target_file is None:
            raise ValueError(f"Could not find '{name}' in {path}")

        # Calculate total files for progress bar
        total_files = len(file_list)
        if supporting_arrays is not None:
            total_files += len(supporting_arrays)

        with zipfile.ZipFile(new_path, "w", zipfile.ZIP_STORED) as new_zip:
            with tqdm.tqdm(total=total_files, desc="Rebuilding checkpoint") as pbar:

                # Copy all files except the target file
                for file_path in file_list:
                    if file_path != target_file:
                        with source_zip.open(file_path) as source_file:
                            data = source_file.read()
                            new_zip.writestr(file_path, data)
                        pbar.update(1)

                # Handle the target file with callback
                with TemporaryDirectory() as temp_dir:
                    # Extract only the target file
                    source_zip.extract(target_file, temp_dir)
                    target_full_path = os.path.join(temp_dir, target_file)

                    # Apply the callback
                    callback(target_full_path)

                    # Add the modified file to the new zip (if it still exists)
                    if os.path.exists(target_full_path):
                        new_zip.write(target_full_path, target_file)
                    pbar.update(1)

                # Add supporting arrays if provided
                if supporting_arrays is not None:
                    for key, entry in supporting_arrays.items():
                        array_path = os.path.join(directory, f"{key}.numpy") if directory else f"{key}.numpy"
                        new_zip.writestr(array_path, entry.tobytes())
                        pbar.update(1)

    os.rename(new_path, path)
    LOG.info("Updated metadata in %s", path)


def replace_metadata(path: str, metadata: dict, supporting_arrays: dict = None, *, name: str = DEFAULT_NAME) -> None:
    """Replace metadata in a checkpoint file.

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    metadata : dict
        A JSON serializable object
    supporting_arrays : dict, optional
        A dictionary of supporting NumPy arrays
    name : str, optional
        The name of the metadata file in the zip archive
    """
    if not isinstance(metadata, dict):
        raise ValueError(f"metadata must be a dict, got {type(metadata)}")

    if "version" not in metadata:
        raise ValueError("metadata must have a 'version' key")

    def callback(full):
        with open(full, "w") as f:
            json.dump(metadata, f)

    return _edit_metadata(path, name, callback, supporting_arrays)


def remove_metadata(path: str, *, name: str = DEFAULT_NAME) -> None:
    """Remove metadata from a checkpoint file.

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    name : str, optional
        The name of the metadata file in the zip archive
    """

    def callback(full):
        os.remove(full)

    return _edit_metadata(path, name, callback)
