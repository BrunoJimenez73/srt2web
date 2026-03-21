@echo off
REM Docker Model Runner - Qwen3-8B-128K Startup Script
REM Configures the model with maximum context and optimal runtime flags

echo ========================================
echo Docker Model Runner - Qwen3-8B-128K
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

echo [1/3] Checking Docker Model Runner status...
curl -s http://localhost:12434/ >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Docker Model Runner is running on port 12434
) else (
    echo [WARNING] Docker Model Runner is not responding on port 12434
    echo [INFO] Starting Docker Model Runner...
    echo [INFO] Open Docker Desktop and enable Model Runner in Settings
)

echo.
echo [2/3] Configuring qwen3-8b-128k-gguf model...
echo.

REM Configure model with 32K context (testing phase)
REM Runtime flags:
REM   --mlock: Lock model in memory for better performance
REM   --batch-size 2048: Larger batch for faster prompt processing
REM   --threads 8: Optimize for 8 CPU threads

docker model configure --context-size 32768 huggingface.co/unsloth/qwen3-8b-128k-gguf:latest -- --mlock --batch-size 2048 --threads 8

if %errorlevel% equ 0 (
    echo [OK] Model configured successfully with:
    echo       - Context size: 32K tokens (131072 max)
    echo       - Runtime flags: --mlock --batch-size 2048 --threads 8
) else (
    echo [WARNING] Configuration may have failed. Check Docker logs.
)

echo.
echo [3/3] Verifying configuration...
echo.

REM Show current model list
echo Available models:
curl -s http://localhost:12434/api/tags 2>nul | findstr /C:"qwen3-8b-128k"

echo.
echo ========================================
echo Configuration complete!
echo ========================================
echo.
echo Current settings for qwen3-8b-128k-gguf:
echo   - Context size: 32K tokens (can be scaled to 128K)
echo   - Runtime flags: --mlock --batch-size 2048 --threads 8
echo.
echo To update to 128K context (after testing):
echo   docker model configure --context-size 131072 huggingface.co/unsloth/qwen3-8b-128k-gguf:latest
echo.
echo To reset to defaults:
echo   docker model configure --context-size -1 huggingface.co/unsloth/qwen3-8b-128k-gguf:latest
echo.

pause
