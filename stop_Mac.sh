#!/bin/bash
# SRT2Web - Script de parada para Mac Silicon
# Funciona en Mac M1/M2/M3 con macOS 12+
# Detiene servidor y TUI.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "==============================================="
echo "         SRT2Web - DETENIENDO"
echo "==============================================="
echo ""

# =============================================
# 1. Buscar procesos TUI (srt2web-tui)
# =============================================
echo -e "${BLUE}[1/3] Buscando TUI...${NC}"

TUI_PIDS=$(pgrep -f "srt2web-tui" 2>/dev/null || echo "")
if [ -n "$TUI_PIDS" ]; then
    echo -e "${GREEN} ✓ TUI encontrada (PIDs: $(echo $TUI_PIDS | tr '\n' ' '))${NC}"
    echo -e "${BLUE} Deteniendo TUI...${NC}"
    kill -TERM $TUI_PIDS 2>/dev/null
    sleep 1
    # Force kill if still running
    for pid in $TUI_PIDS; do
        if ps -p $pid > /dev/null 2>&1; then
            kill -9 $pid 2>/dev/null
        fi
    done
    echo -e "${GREEN} ✓ TUI detenida${NC}"
else
    echo -e "${GREEN} ✓ No hay TUI ejecutándose${NC}"
fi

# =============================================
# 2. Buscar proceso del servidor
# =============================================
echo ""
echo -e "${BLUE}[2/3] Buscando servidor...${NC}"

SERVER_PID=$(pgrep -f "python main.py" 2>/dev/null || pgrep -f "python3 main.py" 2>/dev/null || echo "")

if [ -z "$SERVER_PID" ]; then
    SERVER_PID=$(lsof -ti :9999 2>/dev/null | head -1 || echo "")
fi

if [ -z "$SERVER_PID" ]; then
    echo -e "${YELLOW} ⚠️  No hay servidor ejecutándose${NC}"
else
    echo -e "${GREEN} ✓ Servidor encontrado (PID: $SERVER_PID)${NC}"

    echo ""
    echo -e "${BLUE}[3/3] Deteniendo servidor...${NC}"

    kill -TERM $SERVER_PID 2>/dev/null
    sleep 2

    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo -e "${YELLOW} ⚠️  No respondió a SIGTERM, enviando SIGKILL...${NC}"
        kill -9 $SERVER_PID 2>/dev/null
    fi

    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo -e "${RED} ✗ No se pudo detener el servidor${NC}"
        echo -e "${YELLOW}   Intenta: kill -9 $SERVER_PID${NC}"
        exit 1
    fi

    echo -e "${GREEN} ✓ Servidor detenido${NC}"
fi

# =============================================
# 3. Limpiar puertos (opcional)
# =============================================
echo ""
if lsof -ti :9999 > /dev/null 2>&1; then
    echo -e "${YELLOW} ⚠️  Puerto 9999 aún en uso${NC}"
    echo -e "${YELLOW}   Procesos:${NC}"
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

echo ""
echo "==============================================="
echo "         SERVIDOR DETENIDO"
echo "==============================================="
echo ""
