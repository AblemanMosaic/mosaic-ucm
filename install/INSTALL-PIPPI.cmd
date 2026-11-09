@echo off
setlocal
set "EXPECTED_ROOT=%~1"
if not defined EXPECTED_ROOT (
  echo Enter the runtime manifest root printed in the external UCM-v0.1-release.json.
  set /p "EXPECTED_ROOT=Expected runtime root: "
)
if not defined EXPECTED_ROOT (
  echo.
  echo INSTALL REFUSED - an external runtime root is required.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL-PIPPI.ps1" -ExpectedRuntimeRoot "%EXPECTED_ROOT%"
if errorlevel 1 (echo.&echo INSTALL REFUSED - inspect the diagnostic above.) else (echo.&echo PASS - P/PPI was installed for this user.)
pause

