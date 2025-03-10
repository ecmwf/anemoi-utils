# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Text utilities."""

import re
from collections import defaultdict
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

# https://en.wikipedia.org/wiki/Box-drawing_character


def dotted_line(width=84) -> str:
    """Return a dotted line using '┈'.

    >>> dotted_line(40)
    ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    Parameters
    ----------
    width : int, optional
        Number of characters, by default 84

    Returns
    -------
    str
        The dotted line
    """

    return "┈" * width


# Regular expression to match ANSI escape codes
_ansi_escape = re.compile(r"\x1b\[([0-9;]*[mGKH])")


def _has_ansi_escape(s: str) -> bool:
    """Check if a string contains ANSI escape codes.

    Parameters
    ----------
    s : str
        The string to check.

    Returns
    -------
    bool
        True if the string contains ANSI escape codes, False otherwise.
    """
    return _ansi_escape.search(s) is not None


def _split_tokens(s: str) -> List[Tuple[str, int]]:
    """Split a string into a list of visual characters with their lengths.

    Parameters
    ----------
    s : str
        The string to split.

    Returns
    -------
    list of tuple
        A list of tuples where each tuple contains a visual character and its length.
    """
    from wcwidth import wcswidth

    initial = s
    out = []

    # Function to probe the number of bytes needed to encode the first character
    def probe_utf8(s):
        for i in range(1, 5):
            try:
                s[:i].encode("utf-8")
            except UnicodeEncodeError:
                return i - 1
        return 1

    while s:
        match = _ansi_escape.match(s)
        if match:
            token = match.group(0)
            s = s[len(token) :]
            out.append((token, 0))
        else:
            i = probe_utf8(s)
            token = s[:i]
            s = s[i:]
            out.append((token, wcswidth(token)))

    assert "".join(token for (token, _) in out) == initial, (out, initial)
    return out


def visual_len(s: Union[str, List[Tuple[str, int]]]) -> int:
    """Compute the length of a string as it appears on the terminal.

    Parameters
    ----------
    s : str or list of tuple
        The string or list of visual characters with their lengths.

    Returns
    -------
    int
        The visual length of the string.
    """
    if isinstance(s, str):
        s = _split_tokens(s)
    assert isinstance(s, (tuple, list)), (type(s), s)
    if len(s) == 0:
        return 0
    for _ in s:
        assert isinstance(_, tuple), s
        assert len(_) == 2, s
    n = 0
    for _, width in s:
        n += width
    return n


def boxed(text: str, min_width: int = 80, max_width: int = 80) -> str:
    """Put a box around a text.

    >>> boxed("Hello,\\nWorld!", max_width=40)
    ┌──────────────────────────────────────────┐
    │ Hello,                                   │
    │ World!                                   │
    └──────────────────────────────────────────┘

    Parameters
    ----------
    text : str
        The text to box
    min_width : int, optional
        The minimum width of the box, by default 80
    max_width : int, optional
        The maximum width of the box, by default 80

    Returns
    -------
    str
        A boxed version of the input text
    """

    lines = []
    for line in text.split("\n"):
        line = line.rstrip()
        line = _split_tokens(line)
        lines.append(line)

    width = max(visual_len(_) for _ in lines)

    if min_width is not None:
        width = max(width, min_width)

    if max_width is not None:

        def shorten_line(line, max_width):
            if visual_len(line) > max_width:
                while visual_len(line) >= max_width:
                    line = line[:-1]
                line.append(("…", 1))
            return line

        width = min(width, max_width)
        lines = [shorten_line(line, max_width) for line in lines]

    def pad_line(line, width):
        line = line + [" "] * (width - visual_len(line))
        return line

    lines = [pad_line(line, width) for line in lines]

    box = []
    box.append("┌" + "─" * (width + 2) + "┐")
    for line in lines:
        s = "".join(_[0] for _ in line)
        if _has_ansi_escape(s):
            s += "\x1b[0m"
        box.append(f"│ {s} │")
    box.append("└" + "─" * (width + 2) + "┘")

    return "\n".join(box)


def bold(text: str) -> str:
    """Make the text bold.

    Parameters
    ----------
    text : str
        The text to make bold.

    Returns
    -------
    str
        The bold text.
    """
    from termcolor import colored

    return colored(text, attrs=["bold"])


def red(text: str) -> str:
    """Make the text red.

    Parameters
    ----------
    text : str
        The text to make red.

    Returns
    -------
    str
        The red text.
    """
    from termcolor import colored

    return colored(text, "red")


def green(text: str) -> str:
    """Make the text green.

    Parameters
    ----------
    text : str
        The text to make green.

    Returns
    -------
    str
        The green text.
    """
    from termcolor import colored

    return colored(text, "green")


def blue(text: str) -> str:
    """Make the text blue.

    Parameters
    ----------
    text : str
        The text to make blue.

    Returns
    -------
    str
        The blue text.
    """
    from termcolor import colored

    return colored(text, "blue")


class Tree:
    """Tree data structure.

    Parameters
    ----------
    actor : Any
        The actor associated with the tree node.
    parent : Tree, optional
        The parent tree node, by default None.
    """

    def __init__(self, actor: Any, parent: Optional["Tree"] = None):
        self._actor = actor
        self._kids = []
        self._parent = parent

    def adopt(self, kid: "Tree") -> None:
        """Adopt a child tree node.

        Parameters
        ----------
        kid : Tree
            The child tree node to adopt.
        """
        kid._parent._kids.remove(kid)
        self._kids.append(kid)
        kid._parent = self
        # assert False

    def forget(self) -> None:
        """Forget the current tree node."""
        self._parent._kids.remove(self)
        self._parent = None

    @property
    def is_leaf(self) -> bool:
        """Bool: True if the tree node is a leaf, False otherwise."""
        return len(self._kids) == 0

    @property
    def key(self) -> Tuple:
        """Tuple: The key of the tree node."""
        return tuple(sorted(self._actor.as_dict().items()))

    @property
    def _text(self) -> str:
        """Str: The text representation of the tree node."""
        return self._actor.summary

    @property
    def summary(self) -> str:
        """Str: The summary of the tree node."""
        return self._actor.summary

    def as_dict(self) -> dict:
        """Convert the tree node to a dictionary.

        Returns
        -------
        dict
            The dictionary representation of the tree node.
        """
        return self._actor.as_dict()

    def node(self, actor: Any, insert: bool = False) -> "Tree":
        """Create a new tree node.

        Parameters
        ----------
        actor : Any
            The actor associated with the new tree node.
        insert : bool, optional
            Whether to insert the new tree node at the beginning, by default False.

        Returns
        -------
        Tree
            The new tree node.
        """
        node = Tree(actor, self)
        if insert:
            self._kids.insert(0, node)
        else:
            self._kids.append(node)
        return node

    def print(self) -> None:
        """Print the tree."""
        padding = []

        while self._factorise():
            pass

        self._print(padding)

    def _leaves(self, result: List["Tree"]) -> None:
        """Collect all leaf nodes.

        Parameters
        ----------
        result : list of Tree
            The list to collect the leaf nodes.
        """
        if self.is_leaf:
            result.append(self)
        else:
            for kid in self._kids:
                kid._leaves(result)

    def _factorise(self) -> bool:
        """Factorise the tree.

        Returns
        -------
        bool
            True if the tree was factorised, False otherwise.
        """
        if len(self._kids) == 0:
            return False

        result = False
        for kid in self._kids:
            result = kid._factorise() or result

        if result:
            return True

        same = defaultdict(list)
        for kid in self._kids:
            for grand_kid in kid._kids:
                same[grand_kid.key].append((kid, grand_kid))

        result = False
        n = len(self._kids)
        texts = []
        for text, v in same.items():
            if len(v) == n and n > 1:
                for kid, grand_kid in v:
                    kid._kids.remove(grand_kid)
                texts.append((text, v[1][1]))
                result = True

        for text, actor in reversed(texts):
            self.node(actor, True)

        if result:
            return True

        if len(self._kids) != 1:
            return False

        kid = self._kids[0]
        texts = []
        for grand_kid in list(kid._kids):
            if len(grand_kid._kids) == 0:
                kid._kids.remove(grand_kid)
                texts.append((grand_kid.key, grand_kid))
                result = True

        for text, actor in reversed(texts):
            self.node(actor, True)

        return result

    def _print(self, padding: List[str]) -> None:
        """Print the tree with padding.

        Parameters
        ----------
        padding : list of str
            The padding for each level of the tree.
        """
        for i, p in enumerate(padding[:-1]):
            if p == " └":
                padding[i] = "  "
            if p == " ├":
                padding[i] = " │"
        if padding:
            print(f"{''.join(padding)}─{self._text}")
        else:
            print(self._text)
        padding.append(" ")
        for i, k in enumerate(self._kids):
            sep = " ├" if i < len(self._kids) - 1 else " └"
            padding[-1] = sep
            k._print(padding)

        padding.pop()

    def to_json(self, depth: int = 0) -> dict:
        """Convert the tree to a JSON serializable dictionary.

        Parameters
        ----------
        depth : int, optional
            The depth of the tree, by default 0.

        Returns
        -------
        dict
            The JSON serializable dictionary representation of the tree.
        """
        while self._factorise():
            pass

        return {
            "actor": self._actor.as_dict(),
            "kids": [k.to_json(depth + 1) for k in self._kids],
            "depth": depth,
        }


def table(rows: List[List[Any]], header: List[str], align: List[str], margin: int = 0) -> str:
    """Format a table.

        >>> table([['Aa', 12, 5],
                ['B', 120, 1],
                ['C', 9, 123]],
                ['C1', 'C2', 'C3'],
                ['<', '>', '>'])
            C1 │  C2 │  C3
            ───┼─────┼────
            Aa │  12 │   5
            B  │ 120 │   1
            C  │   9 │ 123
            ───┴─────┴────

    Parameters
    ----------
    rows : list of lists (or tuples)
        The rows of the table
    header : A list or tuple of strings
        The header of the table
    align : A list of '<', '>', or '^'
        To align the columns to the left, right, or center
    margin : int, optional
        Extra spaces on the left side of the table, by default 0

    Returns
    -------
    str
        A table as a string
    """

    def _(x):
        try:
            x = float(x)
        except Exception:
            pass

        if isinstance(x, float):
            return f"{x:g}"

        if isinstance(x, str):
            return x
        if isinstance(x, int):
            return str(x)

        return str(x)

    tmp = []
    for row in rows:
        tmp.append([_(x) for x in row])

    all_rows = [header] + tmp

    lens = [max(len(x) for x in col) for col in zip(*all_rows)]

    result = []
    for i, row in enumerate(all_rows):

        def _(x, i, j):
            if align[j] == "<":
                return x.ljust(i)
            if align[j] == ">":
                return x.rjust(i)
            return x.center(i)

        result.append(" │ ".join([_(x, i, j) for j, (x, i) in enumerate(zip(row, lens))]))
        if i == 0:
            result.append("─┼─".join(["─" * i for i in lens]))

    result.append("─┴─".join(["─" * i for i in lens]))

    if margin:
        result = [margin * " " + x for x in result]

    return "\n".join(result)


def progress(done: int, todo: int, width: int = 80) -> str:
    """Generates a progress bar string.

    Parameters
    ----------

    done : int
        The number of tasks completed.
    todo : int
        The total number of tasks.
    width : int, optional
        The width of the progress bar, by default 80.

    Returns
    -------
    str
        A string representing the progress bar.

    Example
    -------

    >>> print(progress(10, 100,width=50))
    █████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
    """
    done = min(int(done / todo * width + 0.5), width)
    return green("█" * done) + red("█" * (width - done))
