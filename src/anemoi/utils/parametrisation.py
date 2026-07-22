# (C) Copyright 2025 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Abstract *parametrisation* passed to every model and graph constructor.

This replaces the Hydra ``instantiate`` mechanism on the construction path. Modules no
longer receive nested config trees; they receive a :class:`Parametrisation` and read
semantic values from it with :meth:`Parametrisation.get`. Sub-modules that used to be
built with ``instantiate`` are now passed in directly::

    model = MyModel(params, some_layer=MyLayer(params, ...))

``some_layer`` defaults to ``None`` (the module builds its default class), may be a string
(resolved through :meth:`Parametrisation.create_module`, where Hydra can be reattached
later), or an already-built instance.

There is no free-standing ``build`` function: object construction always goes through a
:class:`Parametrisation` instance (``params.create_module(spec, ...)``).

The abstract base lives in ``anemoi.utils`` because it is the lowest layer shared by
``anemoi.graphs``, ``anemoi.models`` and ``anemoi.training``. A :class:`Parametrisation`
round-trips through a plain (JSON-serialisable) dict via :meth:`Parametrisation.to_dict` and
:meth:`Parametrisation.from_dict`; the concrete :class:`DictParametrisation` can be recreated
from that dict. Concrete dict-backed parametrisations subclass
:class:`DictParametrisationBase` (never each other).
"""

from __future__ import annotations

import functools
import importlib
from abc import ABC
from abc import abstractmethod
from typing import Any

__all__ = [
    "Parametrisation",
    "DictParametrisationBase",
    "DictParametrisation",
    "ParametrisationError",
    "MISSING",
    "get_object",
    "get_class",
]

# Sentinel distinguishing "no default given" from ``default=None``.
MISSING: Any = object()

# Keys with a special meaning that must not be forwarded as constructor kwargs.
_SPECIAL_KEYS = frozenset({"_target_", "_args_", "_partial_", "_recursive_", "_convert_"})


class ParametrisationError(Exception):
    """Raised when a parameter is missing or an object cannot be built."""


# --------------------------------------------------------------------------------------
# Dotted-path resolution
# --------------------------------------------------------------------------------------


def get_object(path: str) -> Any:
    """Resolve a dotted import path (``"pkg.mod.attr"``) to the object it names."""
    if not isinstance(path, str) or not path:
        msg = f"_target_ must be a non-empty dotted path, got {path!r}"
        raise ParametrisationError(msg)

    parts = path.split(".")
    for split in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:split])
        try:
            obj: Any = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        try:
            for attr in parts[split:]:
                obj = getattr(obj, attr)
        except AttributeError as err:
            msg = f"Could not resolve attribute path {path!r}: {err}"
            raise ParametrisationError(msg) from err
        return obj

    msg = f"Could not import any module prefix of {path!r}"
    raise ParametrisationError(msg)


def get_class(path: str) -> type:
    """Resolve a dotted path to a class."""
    obj = get_object(path)
    if not isinstance(obj, type):
        msg = f"{path!r} resolved to {type(obj)!r}, expected a class"
        raise ParametrisationError(msg)
    return obj


# --------------------------------------------------------------------------------------
# Construction engine (private -- reached only through Parametrisation.create_module)
# --------------------------------------------------------------------------------------


def _is_mapping(obj: Any) -> bool:
    # dict, DotDict (dict subclass) and OmegaConf DictConfig all expose keys()/__getitem__.
    return hasattr(obj, "keys") and hasattr(obj, "__getitem__") and not isinstance(obj, (str, bytes))


def _is_sequence(obj: Any) -> bool:
    return isinstance(obj, (list, tuple)) or type(obj).__name__ == "ListConfig"


def _has_target(obj: Any) -> bool:
    return _is_mapping(obj) and "_target_" in obj


def _to_plain(obj: Any) -> Any:
    """Coerce OmegaConf / DotDict containers to plain dict / list."""
    if _is_mapping(obj):
        return {k: _to_plain(obj[k]) for k in obj.keys()}
    if _is_sequence(obj):
        return [_to_plain(v) for v in obj]
    return obj


def _resolve_value(value: Any, recursive: bool) -> Any:
    """Resolve a spec value into a constructor argument."""
    if recursive and _has_target(value):
        return _construct(value, _recursive_=recursive)
    if recursive and _is_sequence(value):
        return [_resolve_value(v, recursive) for v in value]
    if recursive and _is_mapping(value):
        return {k: _resolve_value(value[k], recursive) for k in value.keys() if k not in _SPECIAL_KEYS}
    return _to_plain(value)


def _construct(spec: Any, *args: Any, **kwargs: Any) -> Any:
    """Build an object from a ``spec`` without importing Hydra.

    Reached only through :meth:`Parametrisation.create_module`. ``spec`` may be:

    * ``None`` -> ``None``;
    * a dotted-path string -> the named callable is invoked with ``*args, **kwargs``;
    * a mapping with ``_target_`` -> the target is resolved and called, merging spec params
      with call-time kwargs (call-time wins), honouring ``_partial_`` / ``_recursive_`` /
      ``_args_``;
    * a mapping without ``_target_`` -> returned as a (recursively resolved) plain dict;
    * a list/tuple -> element-wise constructed.
    """
    override_partial = kwargs.pop("_partial_", None)
    override_recursive = kwargs.pop("_recursive_", None)

    if spec is None:
        return None

    if isinstance(spec, str):
        target = get_object(spec)
        partial = bool(override_partial)
        return functools.partial(target, *args, **kwargs) if partial else target(*args, **kwargs)

    if _is_sequence(spec):
        recursive = True if override_recursive is None else override_recursive
        return [_resolve_value(v, recursive) for v in spec]

    if not _is_mapping(spec):
        return spec

    if "_target_" not in spec:
        recursive = True if override_recursive is None else override_recursive
        node = _resolve_value(spec, recursive)
        return {**node, **kwargs} if kwargs else node

    target_path = spec["_target_"]
    partial = bool(spec.get("_partial_", False)) if override_partial is None else bool(override_partial)
    recursive = bool(spec.get("_recursive_", True)) if override_recursive is None else bool(override_recursive)

    target = get_object(target_path)

    pos_args = [_resolve_value(a, recursive) for a in (spec.get("_args_") or [])]
    pos_args.extend(args)

    params: dict[str, Any] = {
        key: _resolve_value(spec[key], recursive) for key in spec.keys() if key not in _SPECIAL_KEYS
    }
    params.update(kwargs)

    try:
        if partial:
            return functools.partial(target, *pos_args, **params)
        return target(*pos_args, **params)
    except ParametrisationError:
        raise
    except Exception as err:  # noqa: BLE001 - re-wrap with the offending target for clarity
        msg = f"Error building {target_path!r}: {err}"
        raise ParametrisationError(msg) from err


# --------------------------------------------------------------------------------------
# The abstract Parametrisation
# --------------------------------------------------------------------------------------


class Parametrisation(ABC):
    """Abstract parametrisation passed to model and graph constructors."""

    @abstractmethod
    def get(self, key: str, default: Any = MISSING) -> Any:
        """Return the semantic value for ``key``.

        Raise :class:`ParametrisationError` if ``key`` is absent and no ``default`` is given.
        """

    @abstractmethod
    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation of this parametrisation."""

    def create_module(self, spec: Any, *args: Any, **kwargs: Any) -> Any:
        """Build (or return) a sub-module from ``spec`` -- the single construction entry point.

        Dispatch:

        * a **class** -> instantiated with the runtime args (this is the default sub-module,
          chosen in the constructor signature, i.e. *in the code* rather than the parameters);
        * a **dotted-path string** or a ``_target_`` **mapping** / **list** -> built through
          :meth:`_build_spec` (Hydra-free by default; :class:`HydraParametrisation` overrides
          it to use ``hydra.utils.instantiate``);
        * ``None`` -> ``None``;
        * anything else (an **already-built instance**) -> returned unchanged.
        """
        if isinstance(spec, type):
            kwargs.pop("_recursive_", None)  # spec-build directives don't apply to a class
            kwargs.pop("_partial_", None)
            return spec(*args, **kwargs)
        if spec is None or isinstance(spec, str) or _is_mapping(spec) or _is_sequence(spec):
            return self._build_spec(spec, *args, **kwargs)
        return spec

    def _build_spec(self, spec: Any, *args: Any, **kwargs: Any) -> Any:
        """Construct from a spec (dotted-path string / ``_target_`` mapping / list).

        Hydra-free by default; overridden by :class:`HydraParametrisation`.
        """
        return _construct(spec, *args, **kwargs)

    @classmethod
    def from_dict(cls, data: Any = None) -> "Parametrisation":
        """Build the default (Hydra-free) dict-backed parametrisation from a mapping.

        Callers should use this factory rather than referencing a concrete subclass, so the
        choice of implementation stays behind :class:`Parametrisation`.
        """
        return DictParametrisation(data)


class DictParametrisationBase(Parametrisation):
    """Common base for dict-backed parametrisations -- **not instantiated directly**.

    Holds a JSON-serialisable mapping; keys may be dotted to reach nested values
    (``params.get("model.num_channels")``). Concrete leaves (:class:`DictParametrisation`,
    ``HydraParametrisation``, ``LayerKernels``) subclass this rather than each other, so no
    class that gets instantiated is ever subclassed.
    """

    def __init__(self, data: Any = None) -> None:
        self._data: dict = dict(data) if data is not None else {}

    def get(self, key: str, default: Any = MISSING) -> Any:
        node: Any = self._data
        for part in key.split("."):
            if _is_mapping(node) and part in node:
                node = node[part]
            else:
                if default is MISSING:
                    msg = f"Missing parameter {key!r}"
                    raise ParametrisationError(msg)
                return default
        return node

    def to_dict(self) -> dict:
        return _to_plain(self._data)


class DictParametrisation(DictParametrisationBase):
    """Concrete, Hydra-free parametrisation (recreatable from its dict for inference).

    Prefer constructing it via :meth:`Parametrisation.from_dict`. This leaf is instantiated
    and therefore never subclassed.
    """
