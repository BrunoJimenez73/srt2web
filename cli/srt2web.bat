@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON=python"

if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
    set "PYTHON=%VIRTUAL_ENV%\Scripts\python.exe"
) else if exist "%USERPROFILE%\Documents\programacion\Antigravity\srt2web\venv\Scripts\python.exe" (
    set "PYTHON=%USERPROFILE%\Documents\programacion\Antigravity\srt2web\venv\Scripts\python.exe"
)

"%PYTHON%" "%SCRIPT_DIR%srt2web.py" %*

endlocal