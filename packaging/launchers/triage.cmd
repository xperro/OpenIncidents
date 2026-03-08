@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
py "%SCRIPT_DIR%triage.pyz" %*
