@echo off
setlocal
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONPATH=%~dp0src"
py -3.13 -c "import sys;assert sys.version_info[:2]==(3,13)" >nul 2>&1
if not errorlevel 1 goto run313
py -3.12 -c "import sys;assert sys.version_info[:2]==(3,12)" >nul 2>&1
if not errorlevel 1 goto run312
python -c "import sys;assert (3,12)<=sys.version_info[:2]<(3,14)" >nul 2>&1
if not errorlevel 1 goto runpython
echo PIPPI_PYTHON_312_OR_313_REQUIRED 1>&2
exit /b 2

:run313
py -3.13 -m ucm.pippi_cli %*
exit /b %errorlevel%

:run312
py -3.12 -m ucm.pippi_cli %*
exit /b %errorlevel%

:runpython
python -m ucm.pippi_cli %*
exit /b %errorlevel%
