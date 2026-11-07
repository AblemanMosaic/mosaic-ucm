@echo off
setlocal
call "%~dp0PIPPI.cmd" installer
exit /b %errorlevel%
