@echo off
setlocal
set "UCM_ROOT=%~1"
if "%UCM_ROOT%"=="" set /p UCM_ROOT=Enter the extracted UCM core folder: 
python "%~dp0UCM-AMCAS-ADAPT.py" --ucm-root "%UCM_ROOT%" sidecar-orient
if errorlevel 1 goto :fail
echo.
echo PASS - use UCM-AMCAS-ADAPT.py --ucm-root CORE ucm COMMAND ARGS...
pause
exit /b 0
:fail
echo REFUSED - see the diagnostic above.
pause
exit /b 2
