"""Safe file names and long-path handling shared by every step."""
import os
import re

_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# whitespace + zero-width / bidi / soft-hyphen characters that don't make a name visible
_INVIS = "​‌‍‎‏‪‫‬‭‮⁠⁡⁢⁣⁤⁦⁧⁨⁩﻿­؜᠎"
_EDGE = re.compile(r"^[\s" + _INVIS + r"]+|[\s" + _INVIS + r"]+$")
_DIV_ONLY = re.compile(r"^[\s\-–—_*·•=]+$")
_DIV_WRAP = re.compile(r"^[\-–—_*·•=]+\s*(.*?)\s*[\-–—_*·•=]+$")


def safe(s, n=60):
    """A name that is valid as a file or folder on Windows, macOS and Linux."""
    s = _BAD.sub("_", s or "").strip(" .")
    return s[:n].strip(" .") or "_"


def clean(n):
    """Display name: edge whitespace and invisible characters removed ('' = unnamed)."""
    return _EDGE.sub("", n or "")


def norm(n):
    """For comparing page names: no emoji variation selector, no edge whitespace, case-insensitive."""
    return clean((n or "").replace("️", "")).casefold()


def divider_label(name):
    """None if the page is not a divider (e.g. '-----' or '--- Archive ---'); else its label ('' if unlabeled)."""
    name = clean(name)
    if not name or _DIV_ONLY.match(name):
        return ""
    m = _DIV_WRAP.match(name)
    return m.group(1).strip() if m else None


def lp(path):
    """Windows long-path prefix for paths near the 260-character limit; unchanged elsewhere."""
    path = os.path.abspath(path)
    if os.name == "nt" and len(path) >= 240 and not path.startswith("\\\\?\\"):
        return "\\\\?\\" + path
    return path
