#!/bin/bash
# SRT2Web - Script de parada para Mac Silicon
# Funciona en Mac M1/M2/M3 con macOS 12+

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "==============================================="
echo "         SRT2Web - DETENIENDO"
echo "==============================================="
echo ""

# =============================================
# 1. Buscar proceso del servidor
# =============================================
echo -e "${BLUE}[1/2] Buscando proceso del servidor...${NC}"

# Buscar proceso Python con main.py
SERVER_PID=$(pgrep -f "python main.py" 2>/dev/null || pgrep -f "python3 main.py" 2>/dev/null || echo "")

if [ -z "$SERVER_PID" ]; then
    # Intentar buscar por puerto
    SERVER_PID=$(lsof -ti :9999 2>/dev/null | head -1 || echo "")
fi

if [ -z "$SERVER_PID" ]; then
    echo -e "${YELLOW} ⚠️  No hay servidor ejecutándose${NC}"
    echo ""
    exit 0
fi

echo -e "${GREEN} ✓ Servidor encontrado (PID: $SERVER_PID)${NC}"

# =============================================
# 2. Detener proceso
# =============================================
echo ""
echo -e "${BLUE}[2/2] Deteniendo servidor...${NC}"

# Intentar SIGTERM primero (graceful shutdown)
kill -TERM $SERVER_PID 2>/dev/null

# Esperar un momento
sleep 2

# Verificar si aún está corriendo
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo -e "${YELLOW} ⚠️  El servidor no respondió a SIGTERM, enviando SIGKILL...${NC}"
    kill -9 $SERVER_PID 2>/dev/null
fi

# Verificar que se detuvo
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo -e "${RED} ✗ No se pudo detener el servidor${NC}"
    echo -e "${YELLOW}   Intenta manualmente: kill -9 $SERVER_PID${NC}"
    exit 1
fi

echo -e "${GREEN} ✓ Servidor detenido${NC}"

# =============================================
# 3. Limpiar puertos (opcional)
# =============================================
echo ""
echo -e "${BLUE}[3/3] Verificando puertos...${NC}"

# Verificar si el puerto 9999 está libre
if lsof -ti :9999 > /dev/null 2>&1; then
    echo -e "${YELLOW} ⚠️  Puerto 9999 aún en uso${NC}"
    echo -e "${YELLOW}   Procesos usando el puerto:${NC}"
    lsof -ti :9999 | xargs -I {} ps -p {} -o pid,command 2>/dev/null
    echo ""
    read -p "¿Liberar puerto 9999? (s/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        lsof -ti :9999 | xargs kill -9 2>/dev/null
        echo -e "${GREEN} ✓ Puerto 9999 liberado${NC}"
    fi
else
    echo -e "${GREEN} ✓ Puerto 9999 libre${NC}"
fi

# =============================================
# Resumen
# =============================================
echo ""
echo "==============================================="
echo "         SERVIDOR DETENIDO"
echo "==============================================="
echo ""
echo -e "${GREEN} El servidor SRT2Web ha sido detenido.${NC}"
echo ""