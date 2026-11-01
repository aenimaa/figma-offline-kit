"""Tests never touch the kit folder's own workspace pointer (.workspace): they get a throwaway one."""
import atexit
import os
import shutil
import tempfile

from kit import workspace

_POINTER_DIR = tempfile.mkdtemp(prefix="fok-pointer-")
workspace.POINTER = os.path.join(_POINTER_DIR, ".workspace")
atexit.register(shutil.rmtree, _POINTER_DIR, True)
