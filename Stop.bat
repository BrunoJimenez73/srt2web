@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo  PARADA SRT2WEB
echo ========================================
echo.

REM ---------------------------------------------------------------
REM Parse flags:
REM   (no flag)    -> stop server + auto-clean temp/chunk files
REM   --no-clean   -> just stop, do not remove any output
REM   --clean  -c  -> stop + auto-clean + ALSO wipe logs, pycache,
REM                    tool caches and other build artifacts.
REM   --purge       -> alias of --clean
REM Recordings are NEVER removed by --clean; they are user data.
REM ---------------------------------------------------------------
set "CLEAN_MODE="
set "DO_CLEAN=1"
set "AGGRESSIVE_CLEAN="

:parse_args
if "%~1"=="" goto :args_done
if /I "%~1"=="--clean"    goto :set_aggressive
if /I "%~1"=="-c"         goto :set_aggressive
if /I "%~1"=="--purge"    goto :set_aggressive
if /I "%~1"=="--no-clean" goto :set_no_clean
if /I "%~1"=="--keep-recordings" goto :next_arg
echo [WARNING] Flag desconocido: %~1
goto :next_arg

:set_aggressive
set "CLEAN_MODE=1"
set "AGGRESSIVE_CLEAN=1"
goto :next_arg

:set_no_clean
set "DO_CLEAN=0"
goto :next_arg

:next_arg
shift
goto :parse_args
:args_done

set "PID_FILE=srt2web.pid"
set "FOUND="

REM --- 1. Try PID file ---
if exist "%PID_FILE%" (
    set /p SRT_PID=<"%PID_FILE%"
    echo [INFO] PID file encontrado: !SRT_PID!
    set "FOUND=1"

    tasklist /FI "PID eq !SRT_PID!" 2>nul | findstr /I "python" >nul
    if !errorlevel! equ 0 (
        echo [OK] Deteniendo servidor (PID: !SRT_PID!)
        taskkill /PID !SRT_PID! /F 2>nul
        if !errorlevel! equ 0 (
            echo [OK] Servidor detenido
        ) else (
            echo [WARNING] No se pudo detener via PID
        )
    ) else (
        echo [INFO] Proceso !SRT_PID! ya no existe
    )
    del "%PID_FILE%" 2>nul
)

REM --- 2. Fallback: stop by port ---
if not defined FOUND (
    echo [INFO] PID file no encontrado. Buscando servidor por puerto

    for %%P in (9999 9000 9001 9002 8000 1935) do (
        for /f "skip=1 tokens=5" %%A in ('netstat -ano ^| findstr ":%%P "') do (
            taskkill /PID %%A /F 2>nul
        )
    )
)

REM --- 3. Verify no srt2web ports remain ---
echo.
echo === VERIFICACION ===
set "REMAINING="
for %%P in (9999 9000 9001 9002 8000 1935) do (
    netstat -ano | findstr ":%%P " >nul 2>&1
    if !errorlevel! equ 0 (
        set REMAINING=1
        echo [WARNING] Puerto %%P sigue en uso
    )
)
if defined REMAINING (
    echo [WARNING] Algunos puertos pueden estar ocupados
    echo [INFO] Verifica con: netstat -ano ^| findstr :9999
) else (
    echo [OK] Ningun puerto srt2web en uso
)

REM --- 4. Cleanup of session artifacts ---
REM Always remove chunks/temp/HLS/subtitle staging files left over from the
REM previous pipeline session. They are regenerated on next start; keeping
REM them is what causes "stale images from another session" in the player.
if "%DO_CLEAN%"=="0" (
    echo.
    echo [INFO] --no-clean especificado, no se borraran temporales
    echo.
    goto :end
)

echo.
echo ========================================
echo  LIMPIEZA DE ARCHIVOS DE SESION ANTERIOR
echo ========================================
echo.
echo Se eliminaran temporales de la sesion anterior:
echo   - output\chunks\         (chunks de transcripcion)
echo   - output\temp_audio\     (wav extraidos)
echo   - output\temp_mix\       (wavs mezclados)
echo   - output\temp_tts\       (wavs sintetizados)
echo   - output\hls\seg_*.ts    (segmentos HLS)
echo   - output\hls\*.m3u8      (manifiestos HLS)
echo   - output\subtitles\*.srt (chunks SRT intermedios)
echo   - output\subtitles\subs.vtt (WebVTT rolling)
echo.
echo Se conservaran SIEMPRE:
echo   - output\recordings\     (grabaciones, son datos del usuario)
echo   - logs\                  (logs del sistema)

REM 4a. HLS: segments + manifests + leftover chunk srt
if exist "output\hls" (
    if exist "output\hls\seg_*.ts" del /Q "output\hls\seg_*.ts" 2>nul
    if exist "output\hls\chunk_*.srt" del /Q "output\hls\chunk_*.srt" 2>nul
    if exist "output\hls\stream.m3u8" del /Q "output\hls\stream.m3u8" 2>nul
    if exist "output\hls\master.m3u8" del /Q "output\hls\master.m3u8" 2>nul
    for /f "delims=" %%f in ('dir /b "output\hls\*.m3u8" 2^>nul') do del /Q "output\hls\%%f" 2>nul
)

REM 4b. Subtitle staging chunks + rolling WebVTT
if exist "output\subtitles" (
    if exist "output\subtitles\chunk_*.srt" del /Q "output\subtitles\chunk_*.srt" 2>nul
    if exist "output\subtitles\subs.vtt" del /Q "output\subtitles\subs.vtt" 2>nul
)

REM 4c. Chunks (transcription) - recreate empty
if exist "output\chunks" (
    rd /S /Q "output\chunks" 2>nul
)
mkdir "output\chunks" 2>nul

REM 4d. Temp wavs (audio extract, mix, tts) - recreate empty
for %%d in (temp_audio temp_mix temp_tts) do (
    if exist "output\%%d" (
        rd /S /Q "output\%%d" 2>nul
    )
    mkdir "output\%%d" 2>nul
)

REM 4e. Optional: legacy video/audio dirs if they ever exist
if exist "output\video" rd /S /Q "output\video" 2>nul
if exist "output\audio" rd /S /Q "output\audio" 2>nul

echo.
echo [OK] Temporales de sesion anterior eliminados
echo [OK] output\recordings\ y logs\ conservados

REM --- 5. Aggressive clean (--clean / --purge) ---
if not defined AGGRESSIVE_CLEAN goto :end

echo.
echo ========================================
echo  LIMPIEZA PROFUNDA (--clean)
echo ========================================
echo.
echo Se eliminaran ADEMAS:
echo   - logs\                 (rotara al iniciar)
echo   - __pycache__\ *.pyc    (cache de Python)
echo   - .ruff_cache .mypy_cache .pytest_cache
echo.
set /p "CONFIRM=Confirmar limpieza profunda? (s/n): "
if /I not "!CONFIRM!"=="s" (
    echo Limpieza profunda cancelada
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
if not exist "logs" mkdir "logs" 2>nul

echo [OK] Limpieza profunda completa

:end
echo.
echo ========================================
echo  PROCESO COMPLETADO
echo ========================================
echo.
echo Para iniciar de nuevo: Start.bat
echo Para limpieza maxima:  Stop.bat --clean
echo Para solo parar:       Stop.bat --no-clean
pause
