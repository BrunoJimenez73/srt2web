@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo ========================================
echo  PARADA TOTAL SRT2WEB
echo ========================================
echo.

:: 1. Kill ALL Python, Node, and FFmpeg processes by image name
echo >Killing Python + Node + FFmpeg processes...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM python3.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul
taskkill /F /IM ffmpeg.exe /T 2>nul
taskkill /F /IM ffprobe.exe /T 2>nul
timeout /t 2 >nul

:: 2. Kill any remaining processes on known srt2web ports via PowerShell
echo >Killing processes by port...
powershell -NoProfile -Command ^
  "$ports = @(9999, 9000, 9001, 9002, 8000, 1935, 4321, 5173, 4173);" ^
  "$tcp = Get-NetTCPConnection -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' -and $_.LocalPort -in $ports };" ^
  "foreach ($c in $tcp) { try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop; Write-Host '  Killed PID' $c.OwningProcess 'on port' $c.LocalPort } catch {} }"
timeout /t 1 >nul

:: 3. Second pass: kill any stray processes that might have survived
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM ffmpeg.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul

:: 4. Clean Python caches
echo >Cleaning Python caches...
for /d /r . %%d in (__pycache__) do if exist "%%d" rd /S /Q "%%d" 2>nul
for /f "tokens=*" %%f in ('dir /s /b *.pyc 2^|findstr /v venv node_modules') do if exist "%%f" del /Q "%%f" 2>nul
for /f "tokens=*" %%f in ('dir /s /b *.pyo 2^|findstr /v venv node_modules') do if exist "%%f" del /Q "%%f" 2>nul

:: 5. Clean tool caches
if exist ".ruff_cache" rd /S /Q ".ruff_cache" 2>nul
if exist ".mypy_cache" rd /S /Q ".mypy_cache" 2>nul
if exist ".pytest_cache" rd /S /Q ".pytest_cache" 2>nul
if exist "pytest_tmp_manual" rd /S /Q "pytest_tmp_manual" 2>nul

:: 6. Clean logs dir (recreate empty)
if exist "logs" rd /S /Q "logs" 2>nul
if not exist "logs" mkdir "logs"

:: 7. Clean ALL temp output dirs
echo >Cleaning output temp dirs...
for %%d in (hls subtitles chunks temp_audio temp_mix temp_tts) do (
  if exist "output\%%d" (
    rd /S /Q "output\%%d" 2>nul
    mkdir "output\%%d" 2>nul
  )
)
if exist "output\video" rd /S /Q "output\video" 2>nul
if exist "output\audio" rd /S /Q "output\audio" 2>nul

:: 8. Kill third pass — catch respawns from Windows App execution aliases
timeout /t 1 >nul
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM ffmpeg.exe /T 2>nul

:: 9. Verify no processes remain
echo.
echo === VERIFICATION ===
set "REMAINING="
for /f %%p in ('tasklist /NH /FI "IMAGENAME eq python.exe" 2^>nul ^| findstr /I "python"') do set REMAINING=1
for /f %%p in ('tasklist /NH /FI "IMAGENAME eq ffmpeg.exe" 2^>nul ^| findstr /I "ffmpeg"') do set REMAINING=1
for /f %%p in ('tasklist /NH /FI "IMAGENAME eq node.exe" 2^>nul ^| findstr /I "node"') do set REMAINING=1
if defined REMAINING (
  echo [WARNING] Some processes may still be running.
  tasklist 2>nul | findstr /I "python ffmpeg node" || echo   (none detected)
) else (
  echo [OK] No Python/FFmpeg/Node processes remain.
)

echo.
echo === OUTPUT DIRS ===
for %%d in (hls subtitles chunks temp_audio temp_mix temp_tts) do (
  dir /b "output\%%d" 2>nul >nul && echo   output\%%d: has files || echo   output\%%d: empty
)

echo.
echo ========================================
echo  LIMPIEZA COMPLETA
echo ========================================
echo.
echo Para iniciar de nuevo: Start.bat
pause
