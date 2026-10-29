#!/usr/bin/env python3
"""figma-offline-kit. Run `python kit.py --help`. AI agents: read AGENTS.md first."""
import sys

if sys.version_info < (3, 10):
    sys.exit("figma-offline-kit needs Python 3.10 or newer: https://www.python.org/downloads/")

from kit.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
