@echo off
chcp 65001 >nul
title Servidor-SRT2Web
color 0a

echo ===============================================
echo            INICIANDO SRT2Web
echo ===============================================
echo.
echo [INFO] Verificando entorno de Python...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo [INFO] Por favor, instala Python desde https://python.org
    echo.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo [ERROR] No se encuentra main.py en el directorio actual.
    echo [INFO] Asegurate de ejecutar este script desde la carpeta del proyecto.
    echo.
    pause
    exit /b 1
)

echo [INFO] Verificando dependencias...
if not exist "requirements.txt" (
    echo [WARNING] No se encuentra requirements.txt
) else (
    echo [INFO] Instalando/actualizando dependencias...
    python -m pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo [WARNING] No se pudieron instalar algunas dependencias
        echo [INFO] Intentando continuar de todos modos...
    )
)

echo.
echo [INFO] Iniciando servidor...
echo [INFO] Para detener el servidor, presiona Ctrl+C o cierra esta ventana.
echo.
echo ===============================================
echo Presiona Ctrl+C para detener el servidor
echo ===============================================
echo.

python -X utf8 main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Hubo un problema al iniciar el servidor.
    echo [INFO] Posibles causas:
    echo   - Python no esta correctamente instalado
    echo   - Falta alguna dependencia
    echo   - Puerto 9999 ya esta en uso
    echo   - Problemas de permisos
    echo.
    echo [SOLUCIONES]:
    echo   1. Verifica que Python este instalado: python --version
    echo   2. Instala dependencias: pip install -r requirements.txt
    echo   3. Cambia el puerto en config.yaml si esta ocupado
    echo   4. Ejecuta como administrador si es necesario
    echo.
    pause
)

echo.
echo [INFO] Servidor detenido correctamente
echo.
pause
