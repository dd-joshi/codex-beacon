@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\make-peri6-friend-package.ps1"
set "PERI6_PACKAGE_EXIT=%ERRORLEVEL%"
echo.
if "%PERI6_PACKAGE_EXIT%"=="0" (
  echo The ZIP is ready to send from the dist folder.
) else (
  echo Peri6 friend package creation did not complete.
)
pause
exit /b %PERI6_PACKAGE_EXIT%
