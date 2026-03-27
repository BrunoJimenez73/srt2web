#!/bin/bash

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
WHITE='\033[1;37m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="venv/bin/python3"

echo ""
echo -e "${CYAN}===============================================${NC}"
echo -e "${WHITE}         INICIANDO SRT2Web (Mac)${NC}"
echo -e "${CYAN}===============================================${NC}"
echo ""

# Check venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}[ERROR]${NC} Entorno virtual no encontrado."
    echo "Ejecuta ./install.sh primero."
    exit 1
fi

# Check venv works
if ! "$VENV_PYTHON" --version &>/dev/null; then
    echo -e "${RED}[ERROR]${NC} El entorno virtual no funciona."
    echo "Ejecuta ./install.sh para recrearlo."
    exit 1
fi

# Check FFmpeg
if command -v ffmpeg &>/dev/null; then
    echo -e "${GREEN}[OK]${NC} FFmpeg encontrado."
else
    echo -e "${YELLOW}[WARNING]${NC} FFmpeg no encontrado en PATH."
fi

# Check if port 9999 is already in use
if lsof -ti:9999 &>/dev/null; then
    echo -e "${YELLOW}[WARNING]${NC} Puerto 9999 ya en uso. Ejecuta ./stop.sh primero."
    exit 1
fi

echo ""
echo -e "${GREEN}[OK]${NC} Iniciando servidor en background..."
echo -e "  ${CYAN}Dashboard:${NC} http://localhost:9999"
echo -e "  ${WHITE}Para detener:${NC} ./stop.sh"
echo ""

# Start server in background with nohup
nohup "$VENV_PYTHON" -X utf8 main.py > logs/server.log 2>&1 &
SERVER_PID=$!

# Create logs dir if needed
mkdir -p logs

# Wait a moment and check if it started
sleep 2

if kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Servidor iniciado (PID: ${SERVER_PID})."
    echo -e "  ${CYAN}Logs:${NC} logs/server.log"
else
    echo -e "${RED}[ERROR]${NC} El servidor no pudo iniciar. Revisa logs/server.log"
    if [ -f logs/server.log ]; then
        echo -e "  Ultimas lineas del log:"
        tail -5 logs/server.log
    fi
    exit 1
fi

echo ""
