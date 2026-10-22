@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup-peri6-agent.ps1"
set "PERI6_SETUP_EXIT=%ERRORLEVEL%"
echo.
if not "%PERI6_SETUP_EXIT%"=="0" echo Peri6 Agent setup did not complete.
pause
exit /b %PERI6_SETUP_EXIT%
