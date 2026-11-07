@echo off
setlocal
if "%~1"=="" (
  echo Usage: PIPPI-HEADLESS.BAT PROFILE [OUTPUT.json] 1>&2
  exit /b 64
)
set "PROFILE=%~1"
set "OUTPUT=%~2"
if "%OUTPUT%"=="" set "OUTPUT=%~dp0PIPPI-INSTALL-PLAN.json"
call "%~dp0PIPPI.cmd" install-plan "%PROFILE%" > "%OUTPUT%"
exit /b %errorlevel%
