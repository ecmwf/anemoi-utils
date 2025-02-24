# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import annotations

import functools
from typing import Any
from typing import Callable
from typing import Optional
from typing import Union


def aliases(
    aliases: Optional[dict[str, Union[str, list[str]]]] = None, **kwargs: Any
) -> Callable[[Callable], Callable]:
    """Alias keyword arguments in a function call.

    Allows for dynamically renaming keyword arguments in a function call.

    Parameters
    ----------
    aliases : dict[str, Union[str, list[str]]], optional
        Key, value pair of aliases, with keys being the true name, and value being a str or list of aliases,
        by default None
    **kwargs : Any
        Kwargs form of aliases

    Returns
    -------
    Callable
        Decorator function that renames keyword arguments in a function call.

    Raises
    ------
    ValueError
        If the aliasing would result in duplicate keys.

    Examples
    --------
    ```python
    @aliases(a="b", c=["d", "e"])
    def func(a, c):
        return a, c

    func(a=1, c=2)  # (1, 2)
    func(b=1, d=2)  # (1, 2)
    ```
    """

    if aliases is None:
        aliases = {}
    aliases.update(kwargs)

    aliases = {v: k for k, vs in aliases.items() for v in (vs if isinstance(vs, list) else [vs])}

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            keys = kwargs.keys()
            for k in set(keys).intersection(set(aliases.keys())):
                if aliases[k] in keys:
                    raise ValueError(
                        f"When aliasing {k} with {aliases[k]} duplicate keys were present. Cannot include both."
                    )
                kwargs[aliases[k]] = kwargs.pop(k)

            return func(*args, **kwargs)

        return wrapper

    return decorator
