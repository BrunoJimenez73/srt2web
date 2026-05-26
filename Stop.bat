@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo  PARADA SRT2WEB
echo ========================================
echo.

REM --- Parse --clean flag ---
set "CLEAN_MODE="
if /I "%1"=="--clean" set "CLEAN_MODE=1"
if /I "%1"=="-c" set "CLEAN_MODE=1"

set "PID_FILE=srt2web.pid"
set "FOUND="

REM --- 1. Try PID file ---
if exist "%PID_FILE%" (
    set /p SRT_PID=<"%PID_FILE%"
    echo [INFO] PID file encontrado: !SRT_PID!
    set "FOUND=1"

    REM Verify PID belongs to a python process
    tasklist /FI "PID eq !SRT_PID!" 2>nul | findstr /I "python" >nul
    if !errorlevel! equ 0 (
        echo [OK] Deteniendo servidor (PID: !SRT_PID!)...
        taskkill /PID !SRT_PID! /T /F 2>nul
        if !errorlevel! equ 0 (
            echo [OK] Servidor detenido.
        ) else (
            echo [WARNING] No se pudo detener via PID.
        )
    ) else (
        echo [INFO] Proceso !SRT_PID! ya no existe (previamente detenido).
    )
    del "%PID_FILE%" 2>nul
)

REM --- 2. Fallback: stop by port ---
if not defined FOUND (
    echo [INFO] PID file no encontrado. Buscando servidor por puerto...

    for %%P in (9999 9000 9001 9002 8000 1935) do (
        powershell -NoProfile -Command ^
          "$c = Get-NetTCPConnection -LocalPort %%P -State Listen -ErrorAction SilentlyContinue; if ($c) { try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop; Write-Host '  Detenido proceso en puerto' %%P } catch {} }"
    )
)

REM --- 3. Verify no srt2web ports remain ---
echo.
echo === VERIFICACION ===
set "REMAINING="
for %%P in (9999 9000 9001 9002 8000 1935) do (
    powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort %%P -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
    if !errorlevel! equ 0 (
        set REMAINING=1
        echo [WARNING] Puerto %%P sigue en uso.
    )
)
if defined REMAINING (
    echo [WARNING] Algunos puertos pueden estar ocupados.
    echo [INFO] Verifica con: netstat -ano ^| findstr :9999
) else (
    echo [OK] Ningun puerto srt2web en uso.
)

REM --- 4. Optional cleanup (--clean flag only) ---
if not defined CLEAN_MODE (
    echo.
    echo [INFO] Stop.bat --clean   para limpiar logs, output y caches.
    echo.
    goto :end
)

echo.
echo ========================================
echo  LIMPIEZA DE ARCHIVOS TEMPORALES
echo ========================================
echo.
echo Se eliminaran: logs/ output/temp_* tool caches
echo.

set /p "CONFIRM=Confirmar limpieza? (s/n): "
if /I not "!CONFIRM!"=="s" (
    echo Limpieza cancelada.
    goto :end
)

echo Limpiando...

REM Python caches
for /d /r . %%d in (__pycache__) do if exist "%%d" rd /S /Q "%%d" 2>nul
for /f "tokens=*" %%f in ('dir /s /b *.pyc 2^|findstr /v venv node_modules') do if exist "%%f" del /Q "%%f" 2>nul
for /f "tokens=*" %%f in ('dir /s /b *.pyo 2^|findstr /v venv node_modules') do if exist "%%f" del /Q "%%f" 2>nul

REM Tool caches
for %%d in (.ruff_cache .mypy_cache .pytest_cache pytest_tmp_manual) do (
    if exist "%%d" rd /S /Q "%%d" 2>nul
)

REM Logs dir (recreate empty)
if exist "logs" rd /S /Q "logs" 2>nul
if not exist "logs" mkdir "logs"

REM Output temp dirs
for %%d in (chunks temp_audio temp_mix temp_tts) do (
    if exist "output\%%d" (
        rd /S /Q "output\%%d" 2>nul
        mkdir "output\%%d" 2>nul
    )
)
if exist "output\video" rd /S /Q "output\video" 2>nul
if exist "output\audio" rd /S /Q "output\audio" 2>nul

REM Clean HLS segments (keep dir)
if exist "output\hls" (
    if exist "output\hls\seg_*.ts" del /Q "output\hls\seg_*.ts" 2>nul
    if exist "output\hls\chunk_*.srt" del /Q "output\hls\chunk_*.srt" 2>nul
)

echo [OK] Limpieza completa.

:end
echo.
echo ========================================
echo  PROCESO COMPLETADO
echo ========================================
echo.
echo Para iniciar de nuevo: Start.bat
pause
