"""Small helpers: UTF-8 console, safe file writes, timestamps."""
import json
import os
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wrap(text, indent="", hang=None):
    """Wrap text to the console (at most 76 columns), line by line, never splitting a path or a long word."""
    import shutil
    import textwrap
    width = max(30, min(shutil.get_terminal_size((80, 24)).columns - 2, 76))
    hang = indent if hang is None else hang
    out = []
    for line in str(text).split("\n"):
        out.append(textwrap.fill(line, width, initial_indent=indent, subsequent_indent=hang,
                                 break_long_words=False, break_on_hyphens=False) if line.strip() else line)
    return "\n".join(out)


def md_plain(md):
    """Markdown → plain console text for the guided start: no #, **, `…`, link syntax or command hints."""
    import re
    text = re.sub(r"\s*\((?:run )?`python kit\.py[^`]*`\)", "", md)
    text = re.sub(r"^#+ +", "", text, flags=re.M)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("`", "")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def plural(n, word, many=None):
    """'1 file', '2 files'."""
    return f"{n} {word if n == 1 else (many or word + 's')}"


def size_text(mb):
    """'≈ 24 MB' under 1 GB, '≈ 1.3 GB' above."""
    return f"≈ {round(mb)} MB" if mb < 1000 else f"≈ {mb / 1024:.1f} GB"


def guide(name):
    """Full path of a guide: docs/<name> in the repo, or guides/<name> next to app/ in the download.
    Falls back to the guide on GitHub."""
    for path in (os.path.join(REPO, "docs", name), os.path.join(os.path.dirname(REPO), "guides", name)):
        if os.path.exists(path):
            return path
    return f"https://github.com/aenimaa/figma-offline-kit/blob/main/docs/{name}"


def utf8_console():
    """Windows consoles default to a legacy code page; make print() safe for any text."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def write_text(path, text):
    """Atomic UTF-8 write (no BOM, LF endings), so a crash never leaves half a file."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def write_json(path, data):
    write_text(path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)
