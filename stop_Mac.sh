#!/bin/bash
# SRT2Web - Script de parada para Mac Silicon
# Funciona en Mac M1/M2/M3 con macOS 12+
# Detiene servidor y TUI.
#
# Flags:
#   (no flag)     -> stop server + auto-clean temp/chunk files
#   --no-clean    -> just stop, do not remove any output
#   --clean / -c  -> ALSO wipe logs, pycache, tool caches
#   --purge       -> alias of --clean
# Recordings are NEVER removed; they are user data.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

DO_CLEAN=1
AGGRESSIVE_CLEAN=0
for arg in "$@"; do
    case "$arg" in
        --no-clean)         DO_CLEAN=0 ;;
        --clean|-c|--purge) AGGRESSIVE_CLEAN=1 ;;
        --keep-recordings)  ;; # accepted, default behavior
        *)                  echo -e "${YELLOW}[WARNING] Flag desconocido: $arg${NC}" ;;
    esac
done

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
        echo -e "${BLUE}[1/4] PID file encontrado: $SERVER_PID${NC}"
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
    echo -e "${BLUE}[1/4] PID file no encontrado. Buscando procesos...${NC}"

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
# 3. Limpiar puertos
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
# 4. Limpieza de archivos de sesion anterior
# =============================================
# SIEMPRE (a menos que --no-clean) eliminamos los temporales de la sesion
# anterior: son regenerados al iniciar. Mantenerlos causa "imagenes viejas
# de otra sesion" en el reproductor.
if [ "$DO_CLEAN" = "1" ]; then
    echo ""
    echo -e "${BLUE}===============================================${NC}"
    echo -e "${BLUE} LIMPIEZA DE ARCHIVOS DE SESION ANTERIOR${NC}"
    echo -e "${BLUE}===============================================${NC}"
    echo ""
    echo "Se eliminaran temporales de la sesion anterior:"
    echo "  - output/chunks/         (chunks de transcripcion)"
    echo "  - output/temp_audio/     (wavs extraidos)"
    echo "  - output/temp_mix/       (wavs mezclados)"
    echo "  - output/temp_tts/       (wavs sintetizados)"
    echo "  - output/hls/seg_*.ts    (segmentos HLS)"
    echo "  - output/hls/*.m3u8      (manifiestos HLS)"
    echo "  - output/subtitles/*.srt (chunks SRT intermedios)"
    echo "  - output/subtitles/subs.vtt (WebVTT rolling)"
    echo ""
    echo "Se conservaran SIEMPRE:"
    echo "  - output/recordings/     (grabaciones, son datos del usuario)"
    echo "  - logs/                  (logs del sistema)"

    # HLS
    rm -f output/hls/seg_*.ts output/hls/chunk_*.srt 2>/dev/null
    rm -f output/hls/stream.m3u8 output/hls/master.m3u8 2>/dev/null
    find output/hls -maxdepth 1 -type f -name "*.m3u8" -delete 2>/dev/null

    # Subtitles
    rm -f output/subtitles/chunk_*.srt 2>/dev/null
    rm -f output/subtitles/subs.vtt 2>/dev/null

    # Chunks (transcription) - recreate empty
    rm -rf output/chunks 2>/dev/null && mkdir -p output/chunks

    # Temp wavs
    for d in temp_audio temp_mix temp_tts; do
        rm -rf "output/$d" 2>/dev/null && mkdir -p "output/$d"
    done

    # Optional legacy dirs
    rm -rf output/video output/audio 2>/dev/null

    echo ""
    echo -e "${GREEN} Temporales de sesion anterior eliminados${NC}"
    echo -e "${GREEN} output/recordings/ y logs/ conservados${NC}"
else
    echo ""
    echo -e "${BLUE}[INFO]${NC} --no-clean especificado, no se borraran temporales"
fi

# =============================================
# 5. Limpieza profunda (--clean / --purge)
# =============================================
if [ "$AGGRESSIVE_CLEAN" = "1" ]; then
    echo ""
    echo -e "${YELLOW}===============================================${NC}"
    echo -e "${YELLOW} LIMPIEZA PROFUNDA (--clean)${NC}"
    echo -e "${YELLOW}===============================================${NC}"
    echo ""
    echo "Se eliminaran ADEMAS:"
    echo "  - logs/                 (rotara al iniciar)"
    echo "  - __pycache__/ *.pyc    (cache de Python)"
    echo "  - .ruff_cache .mypy_cache .pytest_cache"
    echo ""
    read -p "Confirmar limpieza profunda? (s/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo "Limpiando..."
        find . -type d -name __pycache__ -not -path "*/venv/*" -not -path "*/node_modules/*" -exec rm -rf {} + 2>/dev/null
        find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -not -path "*/venv/*" -not -path "*/node_modules/*" -delete 2>/dev/null
        rm -rf .ruff_cache .mypy_cache .pytest_cache pytest_tmp_manual 2>/dev/null
        rm -rf logs 2>/dev/null && mkdir logs
        echo -e "${GREEN} Limpieza profunda completa${NC}"
    else
        echo "Limpieza profunda cancelada"
    fi
fi

echo ""
echo "==============================================="
echo "         SERVIDOR DETENIDO"
echo "==============================================="
echo ""
