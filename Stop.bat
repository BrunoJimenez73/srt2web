@echo off
setlocal enabledelayedexpansion

echo ========================================
echo  STOP COMPLETO DE SRT2WEB
echo ========================================

cd /d "%~dp0"

:: 1. Parar SOLO python.exe que ejecuta srt2web (main.py)
echo Deteniendo procesos srt2web...
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" ^
  | Where-Object { $_.CommandLine -like '*main.py*' } ^
  | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" 2>nul
taskkill /F /IM ffmpeg.exe /T 2>nul
taskkill /F /IM ffprobe.exe /T 2>nul
timeout /t 2 >nul

:: 2. Liberar puertos del sistema
echo Liberando puertos...
for %%p in (9999 9000 8000 1935) do (
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr "%%p" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a 2>nul
  )
)
timeout /t 1 >nul

:: 3. Limpiar __pycache__ (archivos compilados temporales)
echo Limpiando caches Python...
for /d /r . %%d in (__pycache__) do (
  rd /S /Q "%%d" 2>nul
)
for /f "tokens=*" %%f in ('dir /s /b *.pyc 2^|findstr /v venv node_modules') do (
  del /Q "%%f" 2>nul
)
for /f "tokens=*" %%f in ('dir /s /b *.pyo 2^|findstr /v venv node_modules') do (
  del /Q "%%f" 2>nul
)
REM NOT deleting .pyd (compiled extension modules, not cache)

:: 4. Limpiar caches de herramientas (NO .cache que contiene modelos ML)
echo Limpiando caches de herramientas...
REM NOT deleting .cache (may contain ML models / piper voices)
if exist ".ruff_cache" rd /S /Q ".ruff_cache" 2>nul
if exist ".mypy_cache" rd /S /Q ".mypy_cache" 2>nul
if exist ".pytest_cache" rd /S /Q ".pytest_cache" 2>nul
if exist "pytest_tmp_manual" rd /S /Q "pytest_tmp_manual" 2>nul

:: 5. Limpiar logs del proyecto
echo Limpiando logs...
if exist "logs" rd /S /Q "logs" 2>nul
if not exist "logs" mkdir "logs"

:: 6. Segunda pasada de limpieza de procesos residuales
echo Limpieza final de procesos...
taskkill /F /IM ffmpeg.exe /T 2>nul
taskkill /F /IM ffprobe.exe /T 2>nul
timeout /t 1 >nul

:: 7. Verificar estado final
echo.
echo === ESTADO FINAL DE LIMPIEZA ===
echo Procesos activos:
tasklist 2^>nul ^| findstr /I "python ffmpeg ffprobe" || echo   Ninguno
echo.
echo Grabacion final (save_video=True genera output\recording.mp4):
if exist "output\recording.mp4" (dir /b "output\recording.mp4" 2^>nul) else echo   No existe
echo.
echo Directorio recording (solo estructura, sin chunks temporales):
if exist "output\recording" (dir /b "output\recording" 2^>nul || echo   Vacio) else echo   No existe
echo.
echo Directorio hls:
if exist "output\hls" (dir /b "output\hls" 2^>nul || echo   Vacio) else echo   No existe
echo.
echo Directorio audio:
if exist "output\audio" (dir /b "output\audio" 2^>nul || echo   Vacio) else echo   No existe
echo.
echo Directorio subtitles:
if exist "output\subtitles" (dir /b "output\subtitles" 2^>nul || echo   Vacio) else echo   No existe
echo.
echo Directorio video:
if exist "output\video" (dir /b "output\video" 2^>nul || echo   Vacio) else echo   No existe
echo.
echo ========================================
echo LIMPIEZA TOTAL COMPLETADA
echo ========================================
echo.
echo Ahora puedes iniciar con: start.bat
pause
