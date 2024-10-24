# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Text utilities"""

import re
from collections import defaultdict

# https://en.wikipedia.org/wiki/Box-drawing_character


def dotted_line(width=84) -> str:
    """Return a dotted line using '┈'

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


def _has_ansi_escape(s):
    return _ansi_escape.search(s) is not None


def _split_tokens(s):
    """Split a string into a list of visual characters with their lenghts."""
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


def visual_len(s):
    """Compute the length of a string as it appears on the terminal."""
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


def boxed(text, min_width=80, max_width=80) -> str:
    """Put a box around a text

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
        line = line.strip()
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


def bold(text):
    from termcolor import colored

    return colored(text, attrs=["bold"])


def red(text):
    from termcolor import colored

    return colored(text, "red")


def green(text):
    from termcolor import colored

    return colored(text, "green")


def blue(text):
    from termcolor import colored

    return colored(text, "blue")


class Tree:
    """Tree data structure."""

    def __init__(self, actor, parent=None):
        self._actor = actor
        self._kids = []
        self._parent = parent

    def adopt(self, kid):
        kid._parent._kids.remove(kid)
        self._kids.append(kid)
        kid._parent = self
        # assert False

    def forget(self):
        self._parent._kids.remove(self)
        self._parent = None

    @property
    def is_leaf(self):
        return len(self._kids) == 0

    @property
    def key(self):
        return tuple(sorted(self._actor.as_dict().items()))

    @property
    def _text(self):
        return self._actor.summary

    @property
    def summary(self):
        return self._actor.summary

    def as_dict(self):
        return self._actor.as_dict()

    def node(self, actor, insert=False):
        node = Tree(actor, self)
        if insert:
            self._kids.insert(0, node)
        else:
            self._kids.append(node)
        return node

    def print(self):
        padding = []

        while self._factorise():
            pass

        self._print(padding)

    def _leaves(self, result):
        if self.is_leaf:
            result.append(self)
        else:
            for kid in self._kids:
                kid._leaves(result)

    def _factorise(self):
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

    def _print(self, padding):
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

    def to_json(self, depth=0):
        while self._factorise():
            pass

        return {
            "actor": self._actor.as_dict(),
            "kids": [k.to_json(depth + 1) for k in self._kids],
            "depth": depth,
        }


def table(rows, header, align, margin=0) -> str:
    """Format a table

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


def progress(done, todo, width=80) -> str:
    """_summary_

    >>> print(progress(10, 100,width=50))
    █████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

    Parameters
    ----------
    done : function
        _description_
    todo : _type_
        _description_
    width : int, optional
        _description_, by default 80

    Returns
    -------
    str
        _description_

    """
    done = min(int(done / todo * width + 0.5), width)
    return green("█" * done) + red("█" * (width - done))
