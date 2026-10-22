@echo off
setlocal
set "PERI6_ROOT=%~dp0"
set "PERI6_PYTHONW=%PERI6_ROOT%.venv\Scripts\pythonw.exe"

if not exist "%PERI6_PYTHONW%" (
  echo Peri6 is not installed in this workspace yet.
  echo Run: .\.venv\Scripts\python -m pip install -e desktop
  pause
  exit /b 1
)

start "Peri6" /d "%PERI6_ROOT%" "%PERI6_PYTHONW%" -m peri6.companion.app %*
