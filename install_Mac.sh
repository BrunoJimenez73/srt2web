#!/bin/bash
# SRT2Web - Instalador para Mac Silicon (ARM64)
# Funciona en Mac M1/M2/M3 con macOS 12+
# Usage: ./install_Mac.sh [--skip-cli] [--skip-dev]

set -e

SKIP_CLI=false
SKIP_DEV=false
for arg in "$@"; do
    case "$arg" in
        --skip-cli) SKIP_CLI=true ;;
        --skip-dev) SKIP_DEV=true ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "==============================================="
echo "         SRT2Web - INSTALADOR MAC"
echo "==============================================="
echo ""

# =============================================
# 0. Verificar arquitectura
# =============================================
echo -e "${BLUE}[0/9] Verificando arquitectura...${NC}"

ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    echo -e "${YELLOW}⚠️  Advertencia: Optimizado para Mac Silicon (ARM64)${NC}"
    echo -e "${YELLOW}   Detectado: $ARCH. Usa Docker o instala manualmente.${NC}"
    echo ""
fi

# =============================================
# 1. Verificar/Instalar Homebrew
# =============================================
echo -e "${BLUE}[1/9] Verificando Homebrew...${NC}"

BREW_INSTALLED=0
if command -v brew &> /dev/null; then
    echo -e "${GREEN} ✓ Homebrew ya instalado${NC}"
    BREW_INSTALLED=1
else
    echo -e "${YELLOW} ⚠️  Homebrew no encontrado${NC}"
    echo " Homebrew es recomendado pero no obligatorio."
    echo ""
    read -p " ¿Instalar Homebrew ahora? (s/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo -e "${BLUE} Instalando Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        if [ "$ARCH" = "arm64" ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        fi
        echo -e "${GREEN} ✓ Homebrew instalado${NC}"
        BREW_INSTALLED=1
    else
        echo -e "${YELLOW} Continuando sin Homebrew.${NC}"
    fi
fi

# =============================================
# 2. Dependencias del sistema
# =============================================
if [ $BREW_INSTALLED -eq 1 ]; then
    echo ""
    echo -e "${BLUE}[2/9] Dependencias del sistema...${NC}"

    if command -v ffmpeg &> /dev/null; then
        echo -e "${GREEN} ✓ FFmpeg ya instalado${NC}"
    else
        echo -e "${BLUE} Instalando FFmpeg...${NC}"
        brew install ffmpeg
        echo -e "${GREEN} ✓ FFmpeg instalado${NC}"
    fi

    if command -v node &> /dev/null; then
        echo -e "${GREEN} ✓ Node.js ya instalado ($(node --version))${NC}"
    else
        echo -e "${BLUE} Instalando Node.js...${NC}"
        brew install node
        echo -e "${GREEN} ✓ Node.js instalado${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}[2/9] Saltando (sin Homebrew). Ten instalados: Python 3.12, FFmpeg, Node.js${NC}"
fi

# =============================================
# 3. Entorno virtual
# =============================================
echo ""
echo -e "${BLUE}[3/9] Entorno virtual...${NC}"

PYTHON_CMD=""
for cmd in python3.12 python3; do
    if command -v "$cmd" &> /dev/null; then
        PYVER=$($cmd --version 2>&1 | awk '{print $2}')
        case "$PYVER" in 3.12*|3.13*) PYTHON_CMD="$cmd"; break ;; esac
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED} ✗ Python 3.12+ no encontrado${NC}"
    echo "   Instala con: brew install python@3.12"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo -e "${BLUE} Creando entorno virtual...${NC}"
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN} ✓ Entorno virtual creado${NC}"
else
    echo -e "${GREEN} ✓ Entorno virtual ya existe${NC}"
fi

source venv/bin/activate

# =============================================
# 4. Core dependencies (sin nvidia-ml-py)
# =============================================
echo ""
echo -e "${BLUE}[4/9] Dependencias core...${NC}"

python -m pip install --upgrade pip wheel setuptools --quiet

# Instalar core sin nvidia-ml-py (no disponible en Mac)
grep -v "nvidia-ml-py" config/requirements.txt > /tmp/srt2web_reqs_core.txt
python -m pip install -r /tmp/srt2web_reqs_core.txt --quiet 2>/dev/null && \
    echo -e "${GREEN} ✓ Core dependencias instaladas${NC}" || \
    echo -e "${YELLOW} ⚠️  Algunas dependencias core fallaron (pueden ser opcionales)${NC}"
rm -f /tmp/srt2web_reqs_core.txt

# =============================================
# 5. CLI dependencies (Textual TUI + HTTP client)
# =============================================
if [ "$SKIP_CLI" = false ]; then
    echo ""
    echo -e "${BLUE}[5/9] CLI / TUI (srt2web-tui)...${NC}"

    if python -m pip install ".[cli]" --quiet 2>/dev/null; then
        echo -e "${GREEN} ✓ CLI/TUI dependencias instaladas${NC}"
    else
        echo -e "${YELLOW} ⚠️  Instalando CLI individualmente...${NC}"
        python -m pip install textual httpx click rich colorama --quiet 2>/dev/null || \
            echo -e "${YELLOW} ⚠️  Algunas CLI deps fallaron (se pueden instalar después)${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}[5/9] CLI saltado (--skip-cli)${NC}"
fi

# =============================================
# 6. Dev dependencies (tests, linting)
# =============================================
if [ "$SKIP_DEV" = false ]; then
    echo ""
    echo -e "${BLUE}[6/9] Dev (tests, linting)...${NC}"

    if python -m pip install ".[dev]" --quiet 2>/dev/null; then
        echo -e "${GREEN} ✓ Dev dependencias instaladas${NC}"
    else
        echo -e "${YELLOW} ⚠️  Algunas dev deps fallaron${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}[6/9] Dev saltado (--skip-dev)${NC}"
fi

# =============================================
# 7. PyTorch con MPS
# =============================================
echo ""
echo -e "${BLUE}[7/9] PyTorch con MPS (GPU Apple Silicon)...${NC}"

MPS_AVAILABLE=$(python -c "import torch; print('MPS' if torch.backends.mps.is_available() else 'CPU')" 2>/dev/null || echo "CPU")
if [ "$MPS_AVAILABLE" = "MPS" ]; then
    echo -e "${GREEN} ✓ PyTorch con MPS ya disponible${NC}"
else
    echo -e "${BLUE} Instalando PyTorch...${NC}"
    python -m pip install torch torchvision torchaudio --quiet 2>/dev/null || \
    python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet 2>/dev/null || \
    echo -e "${YELLOW} ⚠️  PyTorch no instalado (CPU fallback)${NC}"
fi

# =============================================
# 8. ONNX Runtime (CoreML para Apple Silicon)
# =============================================
echo ""
echo -e "${BLUE}[8/9] ONNX Runtime (CoreML)...${NC}"

ONNX_STATUS=$(python -c "import onnxruntime as ort; print('CoreML' if 'CoreMLExecutionProvider' in ort.get_available_providers() else 'CPU')" 2>/dev/null || echo "CPU")
if [ "$ONNX_STATUS" = "CoreML" ]; then
    echo -e "${GREEN} ✓ ONNX Runtime con CoreML ya disponible${NC}"
else
    echo -e "${BLUE} Instalando onnxruntime-silicon...${NC}"
    python -m pip install onnxruntime-silicon --quiet 2>/dev/null || \
    python -m pip install onnxruntime --quiet 2>/dev/null || \
    echo -e "${YELLOW} ⚠️  ONNX Runtime no instalado (CPU fallback)${NC}"
fi

# =============================================
# 9. Modelos Whisper + voces Piper
# =============================================
echo ""
echo -e "${BLUE}[9/9] Modelos...${NC}"

WHISPER_CACHE=".cache/srt2web/whisper"
if [ ! -d "$WHISPER_CACHE/models--Systran--faster-whisper-tiny" ]; then
    echo -e "${BLUE} Descargando Whisper tiny...${NC}"
    python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', download_root='$WHISPER_CACHE')" 2>/dev/null || \
    echo -e "${YELLOW} ⚠️  Se descargará al usar Whisper${NC}"
else
    echo -e "${GREEN} ✓ Whisper tiny ya descargado${NC}"
fi

mkdir -p models/piper
python scripts/download_piper_voices.py 2>/dev/null || \
    echo -e "${YELLOW} ⚠️  Se descargarán al usar Piper${NC}"

# =============================================
# Resumen final
# =============================================
echo ""
echo "==============================================="
echo "           RESUMEN DE INSTALACIÓN"
echo "==============================================="
echo ""

python -c "
import torch
if torch.backends.mps.is_available():
    print('PyTorch: MPS (Apple Silicon GPU)')
elif torch.cuda.is_available():
    print('PyTorch: CUDA')
else:
    print('PyTorch: CPU')
" 2>/dev/null || echo "PyTorch: No verificado"

python -c "
import onnxruntime as ort
providers = ort.get_available_providers()
if 'CoreMLExecutionProvider' in providers:
    print('ONNX: CoreML (Apple Silicon GPU)')
elif 'CUDAExecutionProvider' in providers:
    print('ONNX: CUDA')
else:
    print('ONNX: CPU')
" 2>/dev/null || echo "ONNX: No verificado"

if command -v ffmpeg &> /dev/null; then
    VT=$(ffmpeg -encoders 2>/dev/null | grep -c "h264_videotoolbox" || echo "0")
    if [ "$VT" -gt 0 ]; then
        echo "FFmpeg: OK (VideoToolbox - HW Acceleration)"
    else
        echo "FFmpeg: OK (Software encoding)"
    fi
else
    echo "FFmpeg: No encontrado"
fi

# Verificar CLI
if python -m click --help &>/dev/null 2>&1; then
    echo "CLI/TUI: OK (srt2web-tui disponible)"
else
    echo "CLI/TUI: No instalado (ejecuta sin --skip-cli)"
fi

echo ""
echo "==============================================="
echo "         INSTALACIÓN COMPLETADA"
echo "==============================================="
echo ""
echo " Iniciar servidor:    ./start_Mac.sh"
echo " Iniciar TUI:         source venv/bin/activate && srt2web-tui"
echo " Detener servidor:    ./stop_Mac.sh"
echo ""

chmod +x start_Mac.sh stop_Mac.sh init_Mac.sh 2>/dev/null || true
