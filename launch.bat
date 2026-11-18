@echo off
rem Bootstrap a private Python environment.
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto dependencies
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m venv .venv
) else (
  python -m venv .venv
)
if errorlevel 1 goto failed
:dependencies
".venv\Scripts\python.exe" -c "import numpy, PIL" >nul 2>nul
if not errorlevel 1 goto run
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:run
if /i "%~1"=="desktop" (
  ".venv\Scripts\python.exe" desktop_version\app.py
) else (
  ".venv\Scripts\python.exe" web_version\server.py
)
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Could not start. Install Python 3.11 or 3.12 from python.org.
echo Enable "Add python.exe to PATH" and install Tcl/Tk for desktop mode.
echo First setup requires internet. Review the error above, then retry.
pause
exit /b 1
