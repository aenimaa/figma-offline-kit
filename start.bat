@echo off
rem figma-offline-kit: double-click to start. It walks you through every step.
rem Needs Python 3.10+. If it's missing, this offers to install it (asks first).
setlocal
cd /d "%~dp0"
rem Opened inside the ZIP? Explorer then runs it from a temporary "...zip\" folder.
set "HERE=%~dp0"
if /i not "%HERE:.zip\=%"=="%HERE%" goto notunzipped
set "KIT="
if exist "app\kit.py" set "KIT=app\kit.py"
if not defined KIT if exist "kit.py" set "KIT=kit.py"
if not defined KIT goto notunzipped
set FOK_PAUSE=1
set "CHECK=import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
call :findpython
if defined PY goto run

echo.
echo  figma-offline-kit needs Python 3.10 or newer, and it isn't installed yet.
echo  Python is free. The kit runs on it and installs nothing else.
echo.
set "ANS=Y"
set /p "ANS= Install Python now? [Y/n] "
if /i "%ANS:~0,1%"=="n" goto manual
where winget >nul 2>nul
if errorlevel 1 goto browser
echo.
echo  Installing Python 3.13 for your user with winget, Windows' own installer...
echo.
winget install -e --id Python.Python.3.13 --scope user
call :findpython
if defined PY goto installed
echo.
echo  winget didn't finish the install. Trying the python.org installer instead.
goto browser

:browser
echo.
echo  Opening python.org in your browser:
echo   1. Download Python and run the installer.
echo   2. On its first screen, tick "Add python.exe to PATH", then Install Now.
echo   3. Come back to this window.
start "" https://www.python.org/downloads/windows/
echo.
echo  When the installer has finished, press a key here.
pause >nul
call :findpython
if defined PY goto installed
echo.
echo  Python still isn't found. Close this window and double-click Start.bat again.
pause
exit /b 1

:manual
echo.
echo  OK, nothing was installed. To install Python yourself:
echo   https://www.python.org/downloads/  (tick "Add python.exe to PATH")
echo  Then double-click Start.bat again.
echo.
pause
exit /b 1

:installed
echo.
echo  Python is ready.

:run
%PY% "%KIT%" start %*
exit /b

:notunzipped
echo.
echo  Extract the ZIP first: close this window, right-click the ZIP,
echo  choose "Extract All...", then double-click Start.bat in the new folder.
echo  (Start can't run from inside the ZIP.)
echo.
pause
exit /b 1

:findpython
rem Python on PATH, the py launcher, or a per-user install that PATH doesn't show yet.
set "PY="
py -3 -c "%CHECK%" >nul 2>nul && set "PY=py -3"
if defined PY goto :eof
python -c "%CHECK%" >nul 2>nul && set "PY=python"
if defined PY goto :eof
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  if exist "%%D\python.exe" "%%D\python.exe" -c "%CHECK%" >nul 2>nul && set PY="%%D\python.exe"
)
if defined PY goto :eof
for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore-3*") do (
  if exist "%%D\python.exe" "%%D\python.exe" -c "%CHECK%" >nul 2>nul && set PY="%%D\python.exe"
)
if defined PY goto :eof
if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" -3 -c "%CHECK%" >nul 2>nul && set PY="%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" -3
goto :eof
