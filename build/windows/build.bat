@echo off
setlocal enabledelayedexpansion

echo ================================================
echo SRT2Web Build Script for Windows
echo ================================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
set "BIN_DIR=%PROJECT_ROOT%\bin"
set "BUILD_DIR=%PROJECT_ROOT%\build"

cd /d "%PROJECT_ROOT%"

echo Project root: %PROJECT_ROOT%
echo.

REM Check if FFmpeg exists
if exist "%BIN_DIR%\ffmpeg.exe" (
    echo FFmpeg found at %BIN_DIR%
) else (
    echo FFmpeg not found. Downloading...
    python "%BUILD_DIR%\download_ffmpeg.py" windows
    if errorlevel 1 (
        echo ERROR: Failed to download FFmpeg
        exit /b 1
    )
)

echo.
echo ================================================
echo Step 1: Install PyInstaller (if needed)
echo ================================================
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo ================================================
echo Step 2: Build with PyInstaller
echo ================================================
echo.

REM Clean previous build
if exist "dist\SRT2Web" (
    echo Cleaning previous build...
    rmdir /s /q "dist\SRT2Web"
)

REM Build
pyinstaller "%BUILD_DIR%\windows\SRT2Web.spec" --clean --noconfirm

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)

echo.
echo ================================================
echo Step 3: Copy additional files
echo ================================================

REM Copy config if it doesn't exist in dist
if not exist "dist\SRT2Web\config.yaml" (
    copy "%PROJECT_ROOT%\config.yaml" "dist\SRT2Web\"
)

REM Ensure web directory exists
if not exist "dist\SRT2Web\web" (
    mkdir "dist\SRT2Web\web"
)

echo.
echo ================================================
echo Build Complete!
echo ================================================
echo.
echo Output: dist\SRT2Web\SRT2Web.exe
echo.

REM Calculate size
for /f "tokens=3" %%a in ('dir "dist\SRT2Web" /s /-c ^| find "File(s)"') do set "size=%%a"
echo Total size: !size! bytes

echo.
echo To run: dist\SRT2Web\SRT2Web.exe
echo.

endlocal
