#!/bin/bash

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
WHITE='\033[1;37m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}===============================================${NC}"
echo -e "${WHITE}         DETENIENDO SRT2Web (Mac)${NC}"
echo -e "${CYAN}===============================================${NC}"
echo ""

# =============================================
# 1. Liberar puertos
# =============================================
echo -e "${WHITE}[INFO]${NC} Liberando puertos..."

# Port 9999 (HTTP server)
if lsof -ti:9999 &>/dev/null; then
    for pid in $(lsof -ti:9999); do
        kill -9 "$pid" 2>/dev/null
    done
    echo -e "  ${GREEN}[OK]${NC} Puerto 9999 liberado."
else
    echo -e "  ${CYAN}[INFO]${NC} Puerto 9999 ya libre."
fi

# Port 9000 (SRT input)
if lsof -ti:9000 &>/dev/null; then
    for pid in $(lsof -ti:9000); do
        kill -9 "$pid" 2>/dev/null
    done
    echo -e "  ${GREEN}[OK]${NC} Puerto 9000 liberado."
else
    echo -e "  ${CYAN}[INFO]${NC} Puerto 9000 ya libre."
fi

# =============================================
# 2. Detener procesos
# =============================================
echo ""
echo -e "${WHITE}[INFO]${NC} Deteniendo procesos..."

# Kill main.py processes
if pgrep -f "main.py" &>/dev/null; then
    pkill -9 -f "main.py" 2>/dev/null
    echo -e "  ${GREEN}[OK]${NC} main.py detenido."
else
    echo -e "  ${CYAN}[INFO]${NC} main.py no estaba corriendo."
fi

# Kill ffmpeg processes spawned by this project
if pgrep -f "ffmpeg" &>/dev/null; then
    pkill -9 ffmpeg 2>/dev/null
    echo -e "  ${GREEN}[OK]${NC} FFmpeg detenido."
else
    echo -e "  ${CYAN}[INFO]${NC} FFmpeg no estaba corriendo."
fi

# Kill piper loader subprocesses
if pgrep -f "piper_loader" &>/dev/null; then
    pkill -9 -f "piper_loader" 2>/dev/null
    echo -e "  ${GREEN}[OK]${NC} Piper loader detenido."
fi

# =============================================
# 3. Limpiar archivos temporales
# =============================================
echo ""
echo -e "${WHITE}[INFO]${NC} Limpiando archivos temporales..."

# Clean temp directories
for dir in output/temp_audio output/temp_mix output/temp_tts output/chunks; do
    if [ -d "$dir" ]; then
        rm -rf "$dir"
    fi
done

# Clean HLS files
if [ -d "output/hls" ]; then
    rm -f output/hls/seg_*.ts
    rm -f output/hls/*.m3u8
    rm -f output/hls/*.m4a
    rm -f output/hls/*.mp3
    rm -f output/hls/*.wav
fi

# Reset VTT subtitle file if exists
if [ -f "output/hls/subs.vtt" ]; then
    cat > output/hls/subs.vtt << 'EOF'
WEBVTT

00:00:00.000 --> 00:00:10.000
Esperando stream...
EOF
fi

# Clean temp output files
rm -f output/*.wav output/*.mp3 2>/dev/null

echo -e "  ${GREEN}[OK]${NC} Archivos limpiados."

# =============================================
# Resumen
# =============================================
echo ""
echo -e "${CYAN}===============================================${NC}"
echo -e "${GREEN}          SERVIDOR DETENIDO${NC}"
echo -e "${CYAN}===============================================${NC}"
echo ""
