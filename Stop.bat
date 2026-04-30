@echo off
echo ========================================
echo  STOP COMPLETO DE SRT2WEB
cho ========================================

cd /d C:\Users\bruno\Documents\programacion\Antigravity\srt2web

:: 1. Parar servidor Python y FFmpeg
echo Deteniendo servidor Python y FFmpeg...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM ffmpeg.exe /T 2>nul
timeout /t 3 >nul

:: 2. Limpiar directorios de salida (SIN BORRAR RECORDINGS)
echo Limpiando directorios temporales...
if exist "output\hls" rd /S /Q "output\hls"
if exist "output\temp_mix" rd /S /Q "output\temp_mix"
if not exist "output\hls" mkdir "output\hls"
if not exist "output\temp_mix" mkdir "output\temp_mix"
:: RECORDINGS PROTEGIDOS - NO SE BORRAN
if not exist "output\recording" mkdir "output\recording"

:: 3. Liberar puertos del sistema
echo Liberando puertos del sistema...
for %%p in (9999 9000 8000 1935) do (
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr "%%p" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a 2>nul
  )
)
timeout /t 1 >nul

:: 4. Limpiar caché de Python
echo Limpiando caché Python...
for /d %%d in ("output\__pycache__") do rd /S /Q "%%d"
del /Q "output\*.pyc" 2>nul
del /Q "output\*.pyo" 2>nul

:: 5. Limpiar procesos FFmpeg residuales
echo Limpiando procesos FFmpeg...
taskkill /F /IM ffmpeg.exe /T 2>nul
taskkill /F /IM ffprobe.exe /T 2>nul
timeout /t 2 >nul

:: 6. Limpiar sockets WebSocket si existen
echo Limpiando sockets...
del "output\websocket.sock" 2>nul || true

:: 7. Verificar estado final
echo.
echo === ESTADO FINAL DE LIMPIEZA ===
echo Procesos Python/FFmpeg:
tasklist | findstr /I "python ffmpeg" || echo "  Ninguno (limpio)"
echo.
echo Directorio hls (solo fragmentos):
ls "output\hls" 2>nul || echo "  Vacío"
echo.
echo Directorio recording (DEBE ESTAR COMPLETO):
ls "output\recording" 2>nul || echo "  Vacío"
echo.
echo ========================================
echo LIMPIEZA TOTAL COMPLETADA - SIN RECORDINGS AFECTADOS
echo ========================================
echo.
echo Ahora puedes iniciar con: python main.py
