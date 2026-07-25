# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Hydra-free object construction from configuration dictionaries.

This module provides :class:`Builder`, a small dependency-injection engine that
turns a configuration mapping (the same ``{"_target_": ..., ...}`` shape that
Hydra understands) into live Python objects, *without* depending on Hydra.

The intent is that classes stop calling ``hydra.utils.instantiate`` inside their
own constructors. Instead a :class:`Builder` is injected and used to construct
polymorphic sub-objects, which are then passed to constructors as ordinary
parameters (object injection). Classes that only ever receive fully-built
sub-objects need no knowledge of configuration or of this module at all.

Supported keys in a spec mapping mirror the subset of Hydra features used across
the Anemoi packages:

``_target_``
    Dotted import path of the callable (class or function) to invoke.
``_partial_``
    If truthy, return :func:`functools.partial` bound with the resolved
    arguments instead of calling the target.
``_recursive_``
    If ``False``, nested specs are passed through unchanged rather than being
    built. Defaults to ``True``.
``_convert_``
    Accepted for Hydra compatibility. ``"none"`` (the default) leaves mapping
    and sequence values untouched; ``"all"``/``"partial"`` convert OmegaConf
    containers to plain Python ``dict``/``list``.
"""

from __future__ import annotations

import functools
import importlib
from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any

__all__ = ["Builder", "BuilderError", "as_dict", "build", "build_all", "locate"]


class BuilderError(Exception):
    """Raised when a configuration spec cannot be built into an object."""


def locate(path: str) -> Any:
    """Resolve a dotted import ``path`` to the object it names.

    Supports both module attributes (``package.module.name``) and nested
    attribute access (``package.module.Class.member``).
    """
    if not path:
        raise BuilderError("Empty target path")

    parts = path.split(".")
    # Import the longest importable module prefix, then walk attributes.
    module = None
    index = len(parts)
    while index > 0:
        try:
            module = importlib.import_module(".".join(parts[:index]))
            break
        except ModuleNotFoundError:
            index -= 1
    if module is None:
        # Try importing the first component to surface the real ImportError.
        try:
            importlib.import_module(parts[0])
        except ImportError as exc:  # pragma: no cover - re-raised with context
            raise BuilderError(f"Could not import target {path!r}: {exc}") from exc
        raise BuilderError(f"Could not import target {path!r}")

    obj = module
    for attr in parts[index:]:
        try:
            obj = getattr(obj, attr)
        except AttributeError as exc:
            raise BuilderError(f"Could not resolve attribute {attr!r} of target {path!r}") from exc
    return obj


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _to_container(value: Any) -> Any:
    """Best-effort conversion of OmegaConf containers to plain Python types."""
    try:
        from omegaconf import OmegaConf

        if OmegaConf.is_config(value):
            return OmegaConf.to_container(value, resolve=True)
    except ImportError:
        pass
    return value


def _has_nested_target(value: Any) -> bool:
    """Return True if ``value`` contains a ``_target_`` spec at any depth."""
    if _is_mapping(value):
        if "_target_" in value:
            return True
        return any(_has_nested_target(v) for v in value.values())
    if _is_sequence(value):
        return any(_has_nested_target(v) for v in value)
    return False


class Builder:
    """Construct objects from configuration specs via object injection.

    A ``Builder`` can optionally carry a root configuration mapping so that
    sub-configurations can be looked up by dotted key with :meth:`get`. Its
    central method, :meth:`build`, turns a single spec into a live object while
    merging in runtime-computed keyword arguments.

    Parameters
    ----------
    config : Mapping, optional
        Root configuration this builder carries, enabling :meth:`get`.
    """

    def __init__(self, config: Mapping | None = None) -> None:
        self.config = config

    # -- configuration access -------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        """Return ``config[key]`` following dotted ``key`` notation."""
        node: Any = self.config
        if node is None:
            return default
        for part in key.split("."):
            if _is_mapping(node) and part in node:
                node = node[part]
            else:
                try:
                    node = getattr(node, part)
                except AttributeError:
                    return default
        return node

    # -- construction ---------------------------------------------------------
    def build(self, spec: Any, *args: Any, **runtime_kwargs: Any) -> Any:
        """Build an object from ``spec``.

        Parameters
        ----------
        spec : Mapping or Sequence or Any
            A ``{"_target_": ...}`` mapping is instantiated. A sequence is built
            element-wise. Any other value is returned unchanged.
        *args
            Positional arguments forwarded to the target callable.
        **runtime_kwargs
            Keyword arguments forwarded to the target callable. They override
            values of the same name coming from the spec. Reserved control keys
            (``_partial_``, ``_recursive_``, ``_convert_``) may also be passed to
            override the spec.

        Returns
        -------
        Any
            The constructed object (or a :func:`functools.partial` when partial).
        """
        return self._construct(spec, args, runtime_kwargs, recursive=True)

    __call__ = build

    def _construct(
        self,
        spec: Any,
        args: tuple,
        runtime_kwargs: dict,
        *,
        recursive: bool,
    ) -> Any:
        if _is_mapping(spec) and "_target_" in spec:
            return self._construct_target(spec, args, runtime_kwargs, recursive=recursive)

        # Non-target values ignore positional/keyword runtime overrides. Pure-data
        # structures (no nested target) are returned unchanged to preserve their
        # container type (e.g. OmegaConf DictConfig), mirroring ``_convert_=none``.
        if _is_mapping(spec):
            if not recursive or not _has_nested_target(spec):
                return spec
            return {key: self._construct(value, (), {}, recursive=recursive) for key, value in spec.items()}

        if _is_sequence(spec):
            if not recursive or not _has_nested_target(spec):
                return spec
            return [self._construct(value, (), {}, recursive=recursive) for value in spec]

        return spec

    def _construct_target(
        self,
        spec: Mapping,
        args: tuple,
        runtime_kwargs: dict,
        *,
        recursive: bool,
    ) -> Any:
        control = {"_target_", "_partial_", "_recursive_", "_convert_", "_args_"}

        target_path = spec["_target_"]
        partial = runtime_kwargs.pop("_partial_", spec.get("_partial_", False))
        recursive = runtime_kwargs.pop("_recursive_", spec.get("_recursive_", recursive))
        convert = runtime_kwargs.pop("_convert_", spec.get("_convert_", "none"))
        recursive = bool(recursive)

        target = target_path if callable(target_path) else locate(str(target_path))

        positional = list(spec.get("_args_", ()))
        positional = [self._maybe_build(v, recursive, convert) for v in positional]
        positional.extend(args)

        kwargs: dict[str, Any] = {}
        for key, value in spec.items():
            if key in control:
                continue
            kwargs[key] = self._maybe_build(value, recursive, convert)

        # Runtime kwargs override spec-derived ones.
        kwargs.update(runtime_kwargs)

        try:
            if partial:
                return functools.partial(target, *positional, **kwargs)
            return target(*positional, **kwargs)
        except BuilderError:
            raise
        except Exception as exc:  # noqa: BLE001 - re-raise with context
            raise BuilderError(f"Error building {target_path!r}: {exc}") from exc

    def _maybe_build(self, value: Any, recursive: bool, convert: str) -> Any:
        """Build nested targets when recursing, otherwise return value as-is."""
        if _is_mapping(value) and "_target_" in value:
            if recursive:
                return self._construct(value, (), {}, recursive=recursive)
            return _to_container(value) if convert in ("all", "partial") else value

        if recursive and (_is_mapping(value) or _is_sequence(value)):
            return self._construct(value, (), {}, recursive=recursive)

        if convert in ("all", "partial"):
            return _to_container(value)
        return value


def build(spec: Any, *args: Any, **runtime_kwargs: Any) -> Any:
    """Build a single ``spec`` using a throw-away :class:`Builder`.

    Convenience for call sites that do not need a configuration-carrying builder.
    """
    return Builder().build(spec, *args, **runtime_kwargs)


def build_all(specs: Mapping | Sequence, **runtime_kwargs: Any) -> Any:
    """Build a homogeneous collection of specs, injecting the same kwargs into each.

    Unlike recursive :func:`build`, this forwards ``runtime_kwargs`` to *every*
    element, which is what the many "list/dict of ``_target_`` configs" call sites
    need (node/edge attributes, boundings, scalers, callbacks, pipeline stages).

    Parameters
    ----------
    specs : Mapping or Sequence
        A mapping ``{name: spec}`` or a sequence ``[spec, ...]``. Strings/bytes are
        rejected (they are not collections of specs).
    **runtime_kwargs
        Keyword arguments forwarded to the target of each element.

    Returns
    -------
    dict or list
        Built objects, preserving the input container kind (``dict`` for a mapping,
        ``list`` for a sequence).
    """
    if _is_mapping(specs):
        return {name: build(spec, **runtime_kwargs) for name, spec in specs.items()}
    if _is_sequence(specs):
        return [build(spec, **runtime_kwargs) for spec in specs]
    raise BuilderError(f"build_all expects a mapping or sequence, got {type(specs).__name__}")


def as_dict(config: Any) -> Any:
    """Convert a configuration object to plain Python containers.

    Backward-compatibility shim for the Hydra boundary: an OmegaConf
    ``DictConfig``/``ListConfig`` is materialised (with interpolations resolved)
    into ``dict``/``list``; any other value (including ``DotDict`` and plain
    ``dict``) is returned unchanged. Downstream code then operates purely on plain
    dicts and built objects, free of Hydra/OmegaConf.
    """
    return _to_container(config)
