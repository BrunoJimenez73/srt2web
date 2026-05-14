@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ===============================================
echo            INICIANDO SRT2Web
echo ===============================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Entorno virtual no encontrado.
    echo Ejecuta Install.bat primero.
    pause
    exit /b 1
)

set "PYTHON=venv\Scripts\python.exe"
set "FFMPEG_PATH=%SCRIPT_DIR%bin\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"

set "PORT=9999"
for /f "tokens=2" %%A in ('findstr /C:"  port:" config.yaml 2^>nul') do (
    set "PORT=%%A"
)
set "PORT=!PORT: =!"

echo [INFO] Puerto del servidor: !PORT!

REM Check if port is already in use (only LISTENING = server already running)
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort !PORT! -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
if !errorlevel! equ 0 (
    echo [WARNING] Puerto !PORT! ya esta en uso.
    echo [INFO] El servidor probablemente ya esta corriendo.
    echo.
)

REM Verify FFmpeg exists
echo.
if exist "%FFMPEG_PATH%" (
    echo [OK] FFmpeg encontrado.
    powershell -NoProfile -Command "try { $p = [System.Diagnostics.Process]::Start('\"%FFMPEG_PATH%\"', '-version'); $p.WaitForExit(2000); if ($p.HasExited -and $p.ExitCode -eq 0) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul
    if !errorlevel! equ 0 (
        echo [OK] FFmpeg responde.
    ) else (
        echo [WARNING] FFmpeg no responde o esta bloqueado.
    )
) else (
    echo [WARNING] FFmpeg no encontrado en bin/
)

REM GPU check
echo.
%PYTHON% -c "import torch; print('[GPU] ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else '[GPU] No disponible')" 2>nul

REM ONNX GPU check
powershell -NoProfile -Command "python -c \"import onnxruntime as ort; print('[ONNX] ' + ('GPU' if 'CUDAExecutionProvider' in ort.get_available_providers() else 'CPU'))\"" 2>nul

set "PATH=%SCRIPT_DIR%bin\ffmpeg-master-latest-win64-gpl\bin;%PATH%"

echo.
echo [OK] Iniciando servidor...
echo [INFO] Dashboard: http://localhost:!PORT!
echo [INFO] API: http://localhost:!PORT!/api/docs
echo.

REM Launch server via PowerShell Start-Process (bypasses cmd shell limitations)
powershell -NoProfile -Command "Start-Process -FilePath 'python.exe' -ArgumentList '-X utf8 main.py' -WorkingDirectory '%SCRIPT_DIR%' -PassThru | Select-Object Id, ProcessName" >nul 2>&1

echo [OK] Servidor iniciado.
echo.
echo ===============================================
echo  El servidor se esta ejecutando en:
echo  http://localhost:!PORT!
echo  Dashboard: http://localhost:!PORT!
echo.
echo  Para detener: ejecuta Stop.bat
echo ===============================================
echo.

REM Exit immediately so user can close this window
exit /b 0
