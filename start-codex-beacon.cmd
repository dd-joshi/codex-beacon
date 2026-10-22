@echo off
setlocal
set "CODEX_BEACON_ROOT=%~dp0"
set "CODEX_BEACON_PYTHONW=%CODEX_BEACON_ROOT%.venv\Scripts\pythonw.exe"

if not exist "%CODEX_BEACON_PYTHONW%" (
  echo Codex Beacon is not installed in this workspace yet.
  echo Double-click setup-codex-beacon.cmd first.
  pause
  exit /b 1
)

start "Codex Beacon" /d "%CODEX_BEACON_ROOT%" "%CODEX_BEACON_PYTHONW%" -m codex_beacon.companion.app
