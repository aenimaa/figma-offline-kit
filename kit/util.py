"""Small helpers: UTF-8 console, safe file writes, timestamps."""
import json
import os
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
