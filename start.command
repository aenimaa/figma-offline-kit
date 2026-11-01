#!/bin/bash
# figma-offline-kit: double-click to start (macOS), or run: bash Start.command (Linux).
# Needs Python 3.10+. If it's missing, this offers to install it (asks first).
cd "$(dirname "$0")" || exit 1
if [ -f app/kit.py ]; then KIT=app/kit.py
elif [ -f kit.py ]; then KIT=kit.py
else
  echo
  echo " The kit's files aren't next to this file. Unzip the download first,"
  echo " then double-click Start.command in the new folder."
  read -r -p " Press Enter to close this window."
  exit 1
fi
export FOK_PAUSE=1
CHECK='import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
PKG_VER=3.13.17   # python.org installer offered when Homebrew isn't there

find_python() {
  PY=""
  for py in /opt/homebrew/bin/python3 /usr/local/bin/python3 \
            /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
            python3.14 python3.13 python3.12 python3.11 python3.10 python3 python; do
    p=$(command -v "$py" 2>/dev/null) || continue
    # Without Apple's developer tools, /usr/bin/python3 only opens an install dialog: skip it.
    if [ "$p" = /usr/bin/python3 ] && [ "$(uname)" = Darwin ] && ! xcode-select -p >/dev/null 2>&1; then continue; fi
    if "$p" -c "$CHECK" 2>/dev/null; then PY=$p; return 0; fi
  done
  return 1
}

ask() {
  read -r -p "$1 [Y/n] " a
  case "$a" in [nN]*) return 1 ;; *) return 0 ;; esac
}

if ! find_python; then
  echo
  echo " figma-offline-kit needs Python 3.10 or newer, and it isn't installed yet."
  echo " Python is free. The kit runs on it and installs nothing else."
  echo
  if [ "$(uname)" = Darwin ]; then
    BREW=$(command -v brew || ls /opt/homebrew/bin/brew /usr/local/bin/brew 2>/dev/null | head -n 1)
    if [ -n "$BREW" ]; then
      if ask " Install Python now with Homebrew (brew install python)?"; then
        "$BREW" install python
      fi
    else
      PKG="python-$PKG_VER-macos11.pkg"
      if ask " Download the Python $PKG_VER installer from python.org (about 70 MB) and open it?"; then
        if curl -fL --progress-bar -o "$HOME/Downloads/$PKG" "https://www.python.org/ftp/python/$PKG_VER/$PKG"; then
          open "$HOME/Downloads/$PKG"
          echo " Follow the installer. When it has finished, come back to this window."
        else
          echo " The download failed. Opening python.org instead."
          open https://www.python.org/downloads/macos/
        fi
        read -r -p " Press Enter when Python is installed."
      fi
    fi
  else
    echo " Install Python 3.10 or newer with your package manager (for example: sudo apt install python3)."
  fi
  if ! find_python; then
    echo
    echo " Python isn't found. Install it from https://www.python.org/downloads/"
    echo " and double-click Start.command again."
    read -r -p " Press Enter to close this window."
    exit 1
  fi
  echo " Python is ready."
fi
exec "$PY" "$KIT" start "$@"
