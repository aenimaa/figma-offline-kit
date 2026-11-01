#!/bin/bash
# figma-offline-kit: double-click to start (macOS), or run: bash start.command (Linux).
# It walks you through every step.
cd "$(dirname "$0")" || exit 1
export FOK_PAUSE=1
for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    exec "$py" kit.py start
  fi
done
echo
echo " figma-offline-kit needs Python 3.10 or newer, and it isn't installed yet."
echo
echo " 1. Download it from https://www.python.org/downloads/ (opening it now)"
echo " 2. Install it, then double-click start.command again"
echo
(open https://www.python.org/downloads/ || xdg-open https://www.python.org/downloads/) >/dev/null 2>&1
read -r -p "Press Enter to close this window."
