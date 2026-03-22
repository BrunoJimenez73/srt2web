@echo off
title SRT2Web - Instalador
cd /d "%~dp0"

echo.
echo =======================================================
echo               INSTALADOR SRT2Web v0.5.0
echo =======================================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado.
    echo Por favor instala Python 3.10+ desde python.org
    echo.
    pause
    exit /b 1
)

python -c "import fastapi; import uvicorn" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Instalando dependencias...
    pip install fastapi uvicorn aiohttp psutil gputil --quiet
)

echo [OK] Iniciando instalador...
start /MIN cmd /c "python -m uvicorn instalador.api:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul
start http://localhost:8000/

echo [OK] Instalador abierto en tu navegador.
echo.
pause