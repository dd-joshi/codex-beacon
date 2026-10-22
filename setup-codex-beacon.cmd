@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup-codex-beacon.ps1"
set "CODEX_BEACON_SETUP_EXIT=%ERRORLEVEL%"
echo.
if not "%CODEX_BEACON_SETUP_EXIT%"=="0" echo Codex Beacon setup did not complete.
pause
exit /b %CODEX_BEACON_SETUP_EXIT%
