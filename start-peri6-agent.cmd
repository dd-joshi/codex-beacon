@echo off
setlocal
set "PERI6_ROOT=%~dp0"
set "PERI6_PYTHONW=%PERI6_ROOT%.venv\Scripts\pythonw.exe"

if not exist "%PERI6_PYTHONW%" (
  echo Peri6 Agent is not installed in this workspace yet.
  echo Double-click setup-peri6-agent.cmd first.
  pause
  exit /b 1
)

start "Peri6 Agent" /d "%PERI6_ROOT%" "%PERI6_PYTHONW%" -m peri6.companion.app --agent
