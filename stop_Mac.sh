#!/bin/bash
# SRT2Web - Script de parada para Mac Silicon
# Funciona en Mac M1/M2/M3 con macOS 12+
# Detiene servidor y TUI. Soporta --clean para limpieza adicional.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

CLEAN_MODE=false
if [ "$1" = "--clean" ] || [ "$1" = "-c" ]; then
    CLEAN_MODE=true
fi

echo ""
echo "==============================================="
echo "         SRT2Web - DETENIENDO"
echo "==============================================="
echo ""

PID_FILE="$SCRIPT_DIR/srt2web.pid"
FOUND=false

# =============================================
# 1. Intenta detener por PID file
# =============================================
if [ -f "$PID_FILE" ]; then
    SERVER_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [ -n "$SERVER_PID" ]; then
        echo -e "${BLUE}[1/3] PID file encontrado: $SERVER_PID${NC}"
        FOUND=true

        if ps -p $SERVER_PID > /dev/null 2>&1; then
            echo -e "${GREEN} Deteniendo servidor (PID: $SERVER_PID)...${NC}"
            kill -TERM $SERVER_PID 2>/dev/null
            sleep 2
            if ps -p $SERVER_PID > /dev/null 2>&1; then
                echo -e "${YELLOW} No respondio a SIGTERM, enviando SIGKILL...${NC}"
                kill -9 $SERVER_PID 2>/dev/null
            fi
            echo -e "${GREEN} Servidor detenido${NC}"
        else
            echo -e "${GREEN} Proceso $SERVER_PID ya no existe${NC}"
        fi
    fi
    rm -f "$PID_FILE"
fi

# =============================================
# 2. Fallback: buscar TUI y servidor por patron
# =============================================
if [ "$FOUND" = false ]; then
    echo -e "${BLUE}[1/3] PID file no encontrado. Buscando procesos...${NC}"

    # TUI
    TUI_PIDS=$(pgrep -f "srt2web-tui" 2>/dev/null || echo "")
    if [ -n "$TUI_PIDS" ]; then
        echo -e "${GREEN} TUI encontrada (PIDs: $(echo $TUI_PIDS | tr '\n' ' '))${NC}"
        kill -TERM $TUI_PIDS 2>/dev/null
        sleep 1
        for pid in $TUI_PIDS; do
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null
            fi
        done
        echo -e "${GREEN} TUI detenida${NC}"
    fi

    # Servidor por patron
    SERVER_PID=$(pgrep -f "python.*main.py" 2>/dev/null || echo "")
    if [ -z "$SERVER_PID" ]; then
        SERVER_PID=$(lsof -ti :9999 2>/dev/null | head -1 || echo "")
    fi

    if [ -n "$SERVER_PID" ]; then
        echo -e "${GREEN} Servidor encontrado (PID: $SERVER_PID)${NC}"
        kill -TERM $SERVER_PID 2>/dev/null
        sleep 2
        if ps -p $SERVER_PID > /dev/null 2>&1; then
            kill -9 $SERVER_PID 2>/dev/null
        fi
        echo -e "${GREEN} Servidor detenido${NC}"
    else
        echo -e "${GREEN} No hay servidor ejecutandose${NC}"
    fi
fi

# =============================================
# 3. Limpiar puertos (preguntar si ocupado)
# =============================================
echo ""
if lsof -ti :9999 > /dev/null 2>&1; then
    echo -e "${YELLOW} Puerto 9999 aun en uso${NC}"
    echo -e "${YELLOW}   Procesos:${NC}"
    lsof -ti :9999 | xargs -I {} ps -p {} -o pid,command 2>/dev/null
    echo ""
    read -p "Liberar puerto 9999? (s/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        lsof -ti :9999 | xargs kill -9 2>/dev/null
        echo -e "${GREEN} Puerto 9999 liberado${NC}"
    fi
else
    echo -e "${GREEN} Puerto 9999 libre${NC}"
fi

# =============================================
# 4. Clean mode (opcional)
# =============================================
if [ "$CLEAN_MODE" = true ]; then
    echo ""
    echo -e "${YELLOW}===============================================${NC}"
    echo -e "${YELLOW} LIMPIEZA DE ARCHIVOS TEMPORALES${NC}"
    echo -e "${YELLOW}===============================================${NC}"
    echo ""
    read -p "Confirmar limpieza? (s/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo "Limpiando..."
        rm -rf .ruff_cache .mypy_cache .pytest_cache pytest_tmp_manual 2>/dev/null
        rm -rf logs 2>/dev/null && mkdir logs
        for d in chunks temp_audio temp_mix temp_tts; do
            [ -d "output/$d" ] && rm -rf "output/$d" && mkdir "output/$d" 2>/dev/null
        done
        rm -f output/hls/seg_*.ts output/hls/chunk_*.srt 2>/dev/null
        echo -e "${GREEN} Limpieza completa${NC}"
    else
        echo "Limpieza cancelada"
    fi
fi

echo ""
echo "==============================================="
echo "         SERVIDOR DETENIDO"
echo "==============================================="
echo ""
