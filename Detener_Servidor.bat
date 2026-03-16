@echo off
echo ===============================================
echo            DETENIENDO SRT2Web
echo ===============================================
echo.
echo Buscando y finalizando los procesos de la ventana principal...
taskkill /F /FI "WINDOWTITLE eq Servidor-SRT2Web*" /T >nul 2>&1

echo Buscando procesos en el puerto 8089 (Panel web)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8089') do (
    if "%%a" NEQ "0" (
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo Buscando procesos en el puerto 9000 (Stream SRT)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :9000') do (
    if "%%a" NEQ "0" (
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo.
echo [EXITO] - El servidor y los puertos han sido liberados correctamente.
echo.
pause
