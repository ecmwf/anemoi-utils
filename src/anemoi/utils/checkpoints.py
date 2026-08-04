# (C) Copyright 2024- Anemoi contributors.
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
from typing import Literal
from typing import overload

import numpy as np
import tqdm

LOG = logging.getLogger(__name__)

DEFAULT_NAME = "anemoi.json"
DEFAULT_FOLDER = "anemoi-metadata"

DEPRECATED_NAME = "ai-models.json"


def has_metadata(path: str, *, name: str = DEFAULT_NAME) -> bool:
    """Check if a checkpoint file has a metadata file.

    When *name* is the default metadata name and no matching entry is found,
    this also falls back to the deprecated name (``ai-models.json``) so that
    legacy checkpoints are still detected.

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
    if _has_exact_metadata(path, name=name):
        return True
    if name == DEFAULT_NAME:
        return _has_exact_metadata(path, name=DEPRECATED_NAME)
    return False


def _has_exact_metadata(path: str, *, name: str) -> bool:
    """Check whether a metadata entry with exactly *name* exists (no fallback)."""
    with zipfile.ZipFile(path, "r") as f:
        return any(os.path.basename(b) == name for b in f.namelist())


def get_metadata_path(path: str, *, name: str = DEFAULT_NAME) -> str:
    """Get the full path of the metadata file in the checkpoint.

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    name : str, optional
        The name of the metadata file in the zip archive

    Returns
    -------
    str
        The full path of the metadata file in the zip archive

    Raises
    ------
    FileNotFoundError
        If the metadata file is not found
    ValueError
        If multiple metadata files are found
    """
    with zipfile.ZipFile(path, "r") as f:
        metadata_file = list(filter(lambda b: os.path.basename(b) == name, f.namelist()))
        if len(metadata_file) == 0:
            raise FileNotFoundError(f"Could not find '{name}' in {path}.")
        if len(metadata_file) > 1:
            raise ValueError(f"Found two or more '{name}' in {path}.")
        return metadata_file[0]


def _support_metadata_name_deprecation(path: str, name: str) -> str:
    """Support deprecated metadata name, automatically switching if needed and logging a warning."""
    if name == DEFAULT_NAME and not _has_exact_metadata(path, name=DEFAULT_NAME):
        if _has_exact_metadata(path, name=DEPRECATED_NAME):
            LOG.warning(
                "The metadata file '%s' is deprecated. New versions of checkpoints will write to '%s' instead.",
                DEPRECATED_NAME,
                DEFAULT_NAME,
            )
            name = DEPRECATED_NAME
    return name


# TODO: Refactor this function to reduce complexity
@overload
def load_metadata(
    path: str, *, supporting_arrays: Literal[False] = False, name: str = DEFAULT_NAME
) -> dict:  # type: ignore[reportOverlappingOverload]
    ...


@overload
def load_metadata(
    path: str, *, supporting_arrays: Literal[True] = True, name: str = DEFAULT_NAME
) -> tuple[dict, dict]: ...


def load_metadata(path: str, *, supporting_arrays: bool = False, name: str = DEFAULT_NAME) -> dict | tuple[dict, dict]:
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
    name = _support_metadata_name_deprecation(path, name)
    metadata = get_metadata_path(path, name=name)

    with zipfile.ZipFile(path, "r") as f:
        metadata = json.load(f.open(metadata, "r"))
        if supporting_arrays:
            arrays = load_supporting_arrays(f, metadata.get("supporting_arrays_paths", {}))
            return metadata, arrays
        return metadata


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
        if isinstance(entry, dict) and not set(entry.keys()) == set(["path", "shape", "dtype"]):
            supporting_arrays[key] = load_supporting_arrays(zipf, entry)
        else:
            supporting_arrays[key] = np.frombuffer(
                zipf.read(entry["path"]),
                dtype=entry["dtype"],
            ).reshape(entry["shape"])
    return supporting_arrays


def _get_supporting_arrays_paths(directory: str, folder: str, supporting_arrays: dict | np.ndarray) -> dict:
    """Get the paths of supporting arrays."""
    if supporting_arrays is None:
        return {}

    if isinstance(supporting_arrays, dict):
        return {
            new_key: _get_supporting_arrays_paths(f"{directory}/{folder}", new_key, new_value)
            for new_key, new_value in supporting_arrays.items()
        }

    return dict(
        path=f"{directory}/{folder}.numpy",
        shape=supporting_arrays.shape,
        dtype=str(supporting_arrays.dtype),
    )


def _write_array_to_bytes(array: dict | np.ndarray, name: str, entry: dict, zipf: zipfile.ZipFile) -> None:
    """Write a supporting array to bytes in a zip file."""
    if array is None:
        return

    if isinstance(array, dict):
        for sub_name, sub_array in array.items():
            sub_entry = entry.get(sub_name, {})
            _write_array_to_bytes(sub_array, sub_name, sub_entry, zipf)
        return
    LOG.info(
        "Saving supporting array `%s` to %s (shape=%s, dtype=%s)",
        name,
        entry["path"],
        entry["shape"],
        entry["dtype"],
    )
    zipf.writestr(entry["path"], array.tobytes())


def save_metadata(
    path: str,
    metadata: dict,
    *,
    supporting_arrays: dict | None = None,
    name: str = DEFAULT_NAME,
    folder: str = DEFAULT_FOLDER,
) -> None:
    """Save metadata to a checkpoint file.

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    metadata : dict
        A JSON serializable object
    supporting_arrays : dict | None, optional
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
        metadata["supporting_arrays_paths"] = _get_supporting_arrays_paths(directory, folder, supporting_arrays)

        zipf.writestr(
            f"{directory}/{folder}/{name}",
            json.dumps(metadata),
        )

        _write_array_to_bytes(supporting_arrays, "", metadata["supporting_arrays_paths"], zipf)


def _collect_supporting_array_paths(entry: dict) -> list[str]:
    """Recursively collect the in-archive paths of supporting arrays.

    Parameters
    ----------
    entry : dict
        A ``supporting_arrays_paths`` structure (possibly nested).

    Returns
    -------
    list[str]
        The list of ``.numpy`` archive paths referenced by *entry*.
    """
    paths: list[str] = []
    if isinstance(entry, dict):
        if "path" in entry:
            paths.append(entry["path"])
        else:
            for value in entry.values():
                paths.extend(_collect_supporting_array_paths(value))
    return paths


def _edit_metadata(
    path: str,
    name: str,
    callback: Callable,
    supporting_arrays: dict | None = None,
    *,
    target_file: str | None = None,
    remove_old_arrays: bool = False,
) -> None:
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
    target_file : str, optional
        The in-archive path where the edited metadata should be written. When
        ``None`` (default) the metadata is written back to its original
        location. Set this to migrate a deprecated metadata entry to the
        canonical path.
    remove_old_arrays : bool, optional
        If True, the supporting arrays referenced by the *old* metadata are
        removed from the archive. This is used by :func:`replace_metadata` and
        :func:`remove_metadata` so that stale arrays do not linger.
    """
    new_path = f"{path}.anemoi-edit-{time.time()}-{os.getpid()}.tmp"

    source_file = get_metadata_path(path, name=name)
    if source_file is None:
        raise FileNotFoundError(f"Could not find '{name}' in {path}")

    if target_file is None:
        target_file = source_file

    directory = os.path.dirname(target_file)

    with zipfile.ZipFile(path, "r") as source_zip:
        file_list = source_zip.namelist()

        # Build flat mapping of zip path -> array
        array_paths = {}
        if supporting_arrays is not None:
            for key, entry in supporting_arrays.items():
                if isinstance(entry, dict):
                    # multi-dataset arrays are in a dataset subfolder
                    for sub_key, sub_entry in entry.items():
                        p = f"{key}/{sub_key}.numpy"
                        array_paths[os.path.join(directory, p) if directory else p] = sub_entry
                else:
                    p = f"{key}.numpy"
                    array_paths[os.path.join(directory, p) if directory else p] = entry

        # Skip set for the copy loop: the (old) metadata file and the new
        # array locations (which are re-written below).
        skip_paths = {source_file} | array_paths.keys()

        # Optionally drop the arrays referenced by the old metadata so that
        # stale arrays do not survive a replace/remove.
        if remove_old_arrays:
            try:
                with source_zip.open(source_file) as old_meta_file:
                    old_metadata = json.load(old_meta_file)
                old_array_paths = old_metadata.get("supporting_arrays_paths", {})
                skip_paths.update(_collect_supporting_array_paths(old_array_paths))
            except (json.JSONDecodeError, KeyError):
                pass

        # Calculate total files for progress bar
        total_files = len(file_list) + len(array_paths)

        with zipfile.ZipFile(new_path, "w", zipfile.ZIP_STORED) as new_zip:
            with tqdm.tqdm(total=total_files, desc="Rebuilding checkpoint") as pbar:
                # Copy all files except those being replaced
                for file_path in file_list:
                    if file_path not in skip_paths:
                        with source_zip.open(file_path) as source_file_handle:
                            data = source_file_handle.read()
                            new_zip.writestr(file_path, data)
                        pbar.update(1)

                # Handle the target file with callback
                with TemporaryDirectory() as temp_dir:
                    # Extract only the source metadata file
                    source_zip.extract(source_file, temp_dir)
                    source_full_path = os.path.join(temp_dir, source_file)

                    # Apply the callback
                    callback(source_full_path)

                    # Add the modified file to the new zip (if it still exists),
                    # writing it at the (possibly migrated) target path.
                    if os.path.exists(source_full_path):
                        new_zip.write(source_full_path, target_file)
                    pbar.update(1)

                # Add supporting arrays if provided
                for array_path, array in array_paths.items():
                    new_zip.writestr(array_path, array.tobytes())
                    pbar.update(1)

    os.rename(new_path, path)
    LOG.info("Updated metadata in %s", path)


def replace_metadata(
    path: str,
    metadata: dict,
    supporting_arrays: dict | None = None,
    *,
    name: str = DEFAULT_NAME,
) -> None:
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

    requested_name = name
    name = _support_metadata_name_deprecation(path, name)

    # Unless a custom name was requested, always (re)write the new metadata to
    # the canonical location `<dir>/<folder>/<DEFAULT_NAME>`. This migrates
    # deprecated names (``ai-models.json``) and non-canonical layouts (e.g. a
    # flat ``<dir>/anemoi.json``) to the standard `anemoi-metadata` folder.
    # The top-level directory is the first path component of the existing
    # metadata entry.
    target_file = None
    if requested_name == DEFAULT_NAME:
        source_file = get_metadata_path(path, name=name)
        directory = source_file.split("/")[0]
        if directory:
            target_file = f"{directory}/{DEFAULT_FOLDER}/{DEFAULT_NAME}"

    return _edit_metadata(
        path,
        name,
        callback,
        supporting_arrays,
        target_file=target_file,
        remove_old_arrays=True,
    )


def remove_metadata(path: str, *, name: str = DEFAULT_NAME) -> None:
    """Remove metadata from a checkpoint file.

    Parameters
    ----------
    path : str
        The path to the checkpoint file
    name : str, optional
        The name of the metadata file in the zip archive
    """
    name = _support_metadata_name_deprecation(path, name)

    def callback(full):
        os.remove(full)

    return _edit_metadata(path, name, callback, remove_old_arrays=True)


def unpickle_model(path, **kwargs) -> dict:
    import io

    from peekle import Peekle

    with zipfile.ZipFile(path, "r") as zipf:
        data_files = [name for name in zipf.namelist() if os.path.basename(name) == "data.pkl"]
        if len(data_files) == 0:
            raise FileNotFoundError(f"Could not find 'data.pkl' in {path}.")
        if len(data_files) > 1:
            raise ValueError(f"Found two or more 'data.pkl' in {path}.")
        data = zipf.read(data_files[0])

    parsed = Peekle.parse(io.BytesIO(data))
    return parsed.to_json(**kwargs)
