@echo off
rem figma-offline-kit: double-click to start. It walks you through every step.
cd /d "%~dp0"
set FOK_PAUSE=1
set PY=
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set PY=py -3
if not defined PY python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set PY=python
if not defined PY goto nopython
%PY% kit.py start
exit /b

:nopython
echo.
echo  figma-offline-kit needs Python 3.10 or newer, and it isn't installed yet.
echo.
echo  1. Download it from https://www.python.org/downloads/ (opening it now)
echo  2. On the installer's first screen, tick "Add python.exe to PATH"
echo  3. Double-click start.bat again
echo.
start "" https://www.python.org/downloads/
pause
