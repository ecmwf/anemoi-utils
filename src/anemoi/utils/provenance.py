# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Collect information about the current environment, like:

 - The Python version
 - The versions of the modules which are currently loaded
 - The git information for the modules which are currently loaded from a git repository
 - ...

"""

import datetime
import json
import logging
import os
import subprocess
import sys
import sysconfig
from functools import cache

LOG = logging.getLogger(__name__)


def lookup_git_repo(path):
    from git import InvalidGitRepositoryError
    from git import Repo

    while path != "/":
        try:
            return Repo(path)
        except InvalidGitRepositoryError:
            path = os.path.dirname(path)

    return None


def _check_for_git(paths, full):
    versions = {}
    for name, path in paths:
        repo = lookup_git_repo(path)
        if repo is None:
            continue

        try:

            if not full:
                versions[name] = dict(
                    git=dict(
                        sha1=repo.head.commit.hexsha,
                        modified_files=len([item.a_path for item in repo.index.diff(None)]),
                        untracked_files=len(repo.untracked_files),
                    ),
                )
                continue

            versions[name] = dict(
                path=path,
                git=dict(
                    sha1=repo.head.commit.hexsha,
                    remotes=[r.url for r in repo.remotes],
                    modified_files=sorted([item.a_path for item in repo.index.diff(None)]),
                    untracked_files=sorted(repo.untracked_files),
                ),
            )

        except ValueError as e:
            LOG.error(f"Error checking git repo {path}: {e}")

    return versions


def version(versions, name, module, roots, namespaces, paths, full):
    path = None

    if hasattr(module, "__file__"):
        path = module.__file__
        if path is not None:
            for k, v in roots.items():
                path = path.replace(k, f"<{v}>")

            if path.startswith("/"):
                paths.add((name, path))

    try:
        versions[name] = str(module.__version__)
        return
    except AttributeError:
        pass

    try:
        if path is None:
            namespaces.add(name)
            return

        # For now, don't report on stdlib modules
        if path.startswith("<stdlib>"):
            return

        if full:
            versions[name] = path
        else:
            if not path.startswith("<"):
                versions[name] = os.path.join("...", os.path.basename(path))
        return
    except AttributeError:
        pass

    if name in sys.builtin_module_names:
        return

    versions[name] = str(module)


def _module_versions(full):
    # https://docs.python.org/3/library/sysconfig.html

    roots = {}
    for name, path in sysconfig.get_paths().items():
        if path not in roots:
            roots[path] = name

    # Sort by length of path, so that we get the most specific first
    roots = {path: name for path, name in sorted(roots.items(), key=lambda x: len(x[0]), reverse=True)}

    paths = set()

    versions = {}
    namespaces = set()
    for k, v in sorted(sys.modules.items()):
        if "." not in k:
            version(versions, k, v, roots, namespaces, paths, full)

    # Catter for modules like "earthkit.meteo"
    for k, v in sorted(sys.modules.items()):
        bits = k.split(".")
        if len(bits) == 2 and bits[0] in namespaces:
            version(versions, k, v, roots, namespaces, paths, full)

    return versions, paths


@cache
def package_distributions() -> dict[str, list[str]]:
    # Takes a significant amount of time to run
    # so cache the result
    from importlib import metadata

    # For python 3.9 support
    if not hasattr(metadata, "packages_distributions"):
        import importlib_metadata as metadata

    return metadata.packages_distributions()


def import_name_to_distribution_name(packages: list):
    distribution_names = {}
    package_distribution_names = package_distributions()

    for package in [p for p in packages if p in package_distribution_names]:
        distr_name = package_distribution_names[package]
        if isinstance(distr_name, list):
            if len(distr_name) > 1:
                # Multiple distributions for the same package, i.e. anemoi-graphs, anemoi-utils, ..., Don't know how to handle this
                continue
            distr_name = distr_name[0]

        if distr_name != package:
            distribution_names[package] = distr_name

    return distribution_names


def module_versions(full):
    versions, paths = _module_versions(full)
    git_versions = _check_for_git(paths, full)
    return versions, git_versions


def _name(obj):
    if hasattr(obj, "__name__"):
        if hasattr(obj, "__module__"):
            return f"{obj.__module__}.{obj.__name__}"
        return obj.__name__
    if hasattr(obj, "__class__"):
        return _name(obj.__class__)
    return str(obj)


def _paths(path_or_object):

    if path_or_object is None:
        _, paths = _module_versions(full=False)
        return paths

    if isinstance(path_or_object, (list, tuple, set)):
        paths = []
        for p in path_or_object:
            paths.extend(_paths(p))
        return paths

    if isinstance(path_or_object, str):
        module = sys.modules.get(path_or_object)
        if module is not None:
            return _paths(module)
        return [(path_or_object, path_or_object)]

    if hasattr(path_or_object, "__module__"):
        module = sys.modules.get(path_or_object.__module__)
        return [(path_or_object.__module__, module.__file__)]

    name = _name(path_or_object)
    paths = []
    if hasattr(path_or_object, "__file__"):
        paths.append((name, path_or_object.__file__))

    if hasattr(path_or_object, "__code__"):
        paths.append((name, path_or_object.__code__.co_filename))

    if hasattr(path_or_object, "__module__"):
        module = sys.modules.get(path_or_object.__module__)
        paths.append((name, module.__file__))

    if not paths:
        raise ValueError(f"Could not find path for {name} {path_or_object} {type(path_or_object)}")

    return paths


def git_check(*args) -> dict:
    """Return the git information for the given arguments.

    Arguments can be:
        - an empty list, in that case all loaded modules are checked
        - a module name
        - a module object
        - an object or a class
        - a path to a directory

    Parameters
    ----------
    args : list
        The list of arguments to check

    Returns
    -------
    dict
        An object with the git information for the given arguments.

    >>> {
            "anemoi.utils": {
                "sha1": "c999d83ae283bcbb99f68d92c42d24315922129f",
                "remotes": [
                    "git@github.com:ecmwf/anemoi-utils.git"
                ],
                "modified_files": [
                    "anemoi/utils/checkpoints.py"
                ],
                "untracked_files": []
            }
        }
    """
    paths = _paths(args if len(args) > 0 else None)

    git = _check_for_git(paths, full=True)
    result = {}
    for k, v in git.items():
        result[k] = v["git"]

    return result


def platform_info():
    import platform

    r = {}
    for p in dir(platform):
        if p.startswith("_"):
            continue
        try:
            r[p] = getattr(platform, p)()
        except Exception:
            pass

    def all_empty(x):
        return all(all_empty(v) if isinstance(v, (list, tuple)) else v == "" for v in x)

    for k, v in list(r.items()):
        if isinstance(v, (list, tuple)) and all_empty(v):
            del r[k]

    return r


def gpu_info():
    import nvsmi

    if not nvsmi.is_nvidia_smi_on_path():
        return "nvdia-smi not found"

    try:
        return [json.loads(gpu.to_json()) for gpu in nvsmi.get_gpus()]
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8").strip()


def path_md5(path):
    import hashlib

    hash = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hash.update(chunk)
    return hash.hexdigest()


def assets_info(paths):
    result = {}

    for path in paths:
        try:
            (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(path)  # noqa: F841
            md5 = path_md5(path)
        except Exception as e:
            result[path] = str(e)
            continue

        result[path] = dict(
            size=size,
            atime=datetime.datetime.fromtimestamp(atime).isoformat(),
            mtime=datetime.datetime.fromtimestamp(mtime).isoformat(),
            ctime=datetime.datetime.fromtimestamp(ctime).isoformat(),
            md5=md5,
        )

        try:
            from .checkpoint import peek

            result[path]["peek"] = peek(path)
        except Exception:
            pass

    return result


def gather_provenance_info(assets=[], full=False) -> dict:
    """Gather information about the current environment

    Parameters
    ----------
    assets : list, optional
        A list of file paths for which to collect the MD5 sum, the size and time attributes, by default []
    full : bool, optional
        If true, will also collect various paths, by default False

    Returns
    -------
    dict
        A dictionary with the collected information
    """
    executable = sys.executable

    versions, git_versions = module_versions(full)

    if not full:
        return dict(
            time=datetime.datetime.utcnow().isoformat(),
            python=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            module_versions=versions,
            distribution_names=import_name_to_distribution_name(versions.keys()),
            git_versions=git_versions,
        )
    else:
        return dict(
            time=datetime.datetime.utcnow().isoformat(),
            executable=executable,
            args=sys.argv,
            python_path=sys.path,
            config_paths=sysconfig.get_paths(),
            module_versions=versions,
            distribution_names=import_name_to_distribution_name(versions.keys()),
            git_versions=git_versions,
            platform=platform_info(),
            gpus=gpu_info(),
            assets=assets_info(assets),
        )
