#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
WHITE='\033[1;37m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_VERSION="3.12"
VENV_PYTHON="venv/bin/python3"
NEED_REBOOT=0

echo ""
echo -e "${CYAN}===============================================${NC}"
echo -e "${WHITE}         SRT2Web - INSTALADOR (Mac)${NC}"
echo -e "${CYAN}===============================================${NC}"
echo ""

# =============================================
# 1. Verificar/Instalar pyenv + Python 3.12
# =============================================
echo -e "${WHITE}[1/6] Python ${PYTHON_VERSION} (pyenv)...${NC}"

# Check if pyenv is installed
if ! command -v pyenv &>/dev/null; then
    echo -e "  ${YELLOW}[INFO]${NC} Instalando pyenv via Homebrew..."
    if ! command -v brew &>/dev/null; then
        echo -e "  ${RED}[ERROR]${NC} Homebrew no encontrado. Instala Homebrew primero:"
        echo -e "         https://brew.sh"
        exit 1
    fi
    brew install pyenv
    echo -e "  ${GREEN}[OK]${NC} pyenv instalado."
fi

# Ensure pyenv is in PATH for this session
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Check if Python 3.12 is already installed via pyenv
if pyenv versions --bare 2>/dev/null | grep -q "^${PYTHON_VERSION}"; then
    echo -e "  ${GREEN}[OK]${NC} Python ${PYTHON_VERSION} ya instalado en pyenv."
else
    echo -e "  ${YELLOW}[INFO]${NC} Instalando Python ${PYTHON_VERSION} via pyenv (puede tardar varios minutos)..."
    pyenv install ${PYTHON_VERSION}
    echo -e "  ${GREEN}[OK]${NC} Python ${PYTHON_VERSION} instalado."
fi

PYENV_PYTHON="$PYENV_ROOT/versions/${PYTHON_VERSION}/bin/python${PYTHON_VERSION}"
if [ ! -f "$PYENV_PYTHON" ]; then
    # Try without version suffix
    PYENV_PYTHON="$PYENV_ROOT/versions/${PYTHON_VERSION}/bin/python3"
fi
if [ ! -f "$PYENV_PYTHON" ]; then
    PYENV_PYTHON="$PYENV_ROOT/versions/${PYTHON_VERSION}/bin/python"
fi

if [ ! -f "$PYENV_PYTHON" ]; then
    echo -e "  ${RED}[ERROR]${NC} No se encuentra Python ${PYTHON_VERSION} en pyenv."
    exit 1
fi

echo -e "  ${GREEN}[OK]${NC} Python bin: $PYENV_PYTHON"

# =============================================
# 2. Verificar/Crear entorno virtual
# =============================================
echo ""
echo -e "${WHITE}[2/6] Entorno virtual...${NC}"

if [ -f "$VENV_PYTHON" ]; then
    # Verify it works
    if "$VENV_PYTHON" --version &>/dev/null; then
        echo -e "  ${GREEN}[OK]${NC} Ya existe y funciona."
    else
        echo -e "  ${YELLOW}[WARN]${NC} Entorno virtual corrupto. Recreando..."
        rm -rf venv
        "$PYENV_PYTHON" -m venv venv
        NEED_REBOOT=1
        echo -e "  ${GREEN}[OK]${NC} Entorno virtual recreado."
    fi
else
    echo -e "  ${YELLOW}[INFO]${NC} Creando con Python ${PYTHON_VERSION}..."
    "$PYENV_PYTHON" -m venv venv
    if [ -f "$VENV_PYTHON" ]; then
        NEED_REBOOT=1
        echo -e "  ${GREEN}[OK]${NC} Entorno virtual creado."
    else
        echo -e "  ${RED}[ERROR]${NC} No se pudo crear el entorno virtual."
        exit 1
    fi
fi

# =============================================
# 3. Verificar/Instalar dependencias pip
# =============================================
echo ""
echo -e "${WHITE}[3/6] Dependencias Python...${NC}"

"$VENV_PYTHON" -m pip install --upgrade pip --quiet 2>/dev/null

DEPS_MISSING=0
"$VENV_PYTHON" -c "import fastapi" 2>/dev/null || DEPS_MISSING=1
"$VENV_PYTHON" -c "import faster_whisper" 2>/dev/null || DEPS_MISSING=1
"$VENV_PYTHON" -c "import piper" 2>/dev/null || DEPS_MISSING=1

if [ "$DEPS_MISSING" -eq 1 ]; then
    echo -e "  ${YELLOW}[INFO]${NC} Instalando dependencias desde requirements-mac.txt..."
    "$VENV_PYTHON" -m pip install -r config/requirements-mac.txt --quiet
    echo -e "  ${GREEN}[OK]${NC} Dependencias instaladas."
else
    echo -e "  ${GREEN}[OK]${NC} Dependencias ya instaladas."
fi

# Check onnxruntime providers (CoreML should be available on Apple Silicon)
ORT_CHECK=$("$VENV_PYTHON" -c "
import onnxruntime as ort
providers = ort.get_available_providers()
has_coreml = 'CoreMLExecutionProvider' in providers
has_cpu = 'CPUExecutionProvider' in providers
print(f'coreml={has_coreml} cpu={has_cpu} providers={providers}')
" 2>/dev/null || echo "error")

if [[ "$ORT_CHECK" == *"coreml=True"* ]]; then
    echo -e "  ${GREEN}[OK]${NC} onnxruntime con CoreML (aceleracion Apple Silicon)."
elif [[ "$ORT_CHECK" == *"cpu=True"* ]]; then
    echo -e "  ${YELLOW}[INFO]${NC} onnxruntime sin CoreML (usando CPU)."
elif [[ "$ORT_CHECK" == "error" ]]; then
    echo -e "  ${YELLOW}[INFO]${NC} Instalando onnxruntime..."
    "$VENV_PYTHON" -m pip install onnxruntime --quiet
    echo -e "  ${GREEN}[OK]${NC} onnxruntime instalado."
fi

# Verify key packages
for pkg in edge_tts argostranslate; do
    "$VENV_PYTHON" -c "import $pkg" 2>/dev/null && \
        echo -e "  ${GREEN}[OK]${NC} ${pkg}." || \
        echo -e "  ${YELLOW}[WARN]${NC} ${pkg} no encontrado."
done

# =============================================
# 4. Verificar/Instalar FFmpeg
# =============================================
echo ""
echo -e "${WHITE}[4/6] FFmpeg...${NC}"

if command -v ffmpeg &>/dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -1)
    echo -e "  ${GREEN}[OK]${NC} ${FFMPEG_VERSION}"
    
    # Check SRT support
    SRT_CHECK=$(ffmpeg -protocols 2>&1 | grep -c "srt" || true)
    if [ "$SRT_CHECK" -gt 0 ]; then
        echo -e "  ${GREEN}[OK]${NC} Soporte SRT habilitado."
    else
        echo -e "  ${YELLOW}[WARN]${NC} FFmpeg sin soporte SRT. Reinstala con:"
        echo -e "         brew reinstall ffmpeg --with-srt"
    fi

    # Check VideoToolbox encoder
    VTB_CHECK=$(ffmpeg -encoders 2>&1 | grep -c "videotoolbox" || true)
    if [ "$VTB_CHECK" -gt 0 ]; then
        echo -e "  ${GREEN}[OK]${NC} VideoToolbox encoder disponible."
    else
        echo -e "  ${YELLOW}[INFO]${NC} VideoToolbox no disponible (encoding por CPU)."
    fi
else
    echo -e "  ${YELLOW}[INFO]${NC} FFmpeg no encontrado. Instalando via Homebrew..."
    if command -v brew &>/dev/null; then
        brew install ffmpeg
        echo -e "  ${GREEN}[OK]${NC} FFmpeg instalado."
    else
        echo -e "  ${RED}[ERROR]${NC} Homebrew no encontrado. Instala FFmpeg manualmente:"
        echo -e "         brew install ffmpeg"
        echo -e "         o descarga desde https://ffmpeg.org/download.html"
    fi
fi

# =============================================
# 5. Verificar CoreML / GPU
# =============================================
echo ""
echo -e "${WHITE}[5/6] CoreML / GPU...${NC}"

ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    echo -e "  ${GREEN}[OK]${NC} Apple Silicon (arm64) detectado."
    
    COREML_STATUS=$("$VENV_PYTHON" -c "
import onnxruntime as ort
providers = ort.get_available_providers()
if 'CoreMLExecutionProvider' in providers:
    print('available')
else:
    print('not_available')
" 2>/dev/null || echo "error")

    if [[ "$COREML_STATUS" == "available" ]]; then
        echo -e "  ${GREEN}[OK]${NC} CoreML Execution Provider disponible."
        echo -e "  ${CYAN}[INFO]${NC} Whisper y Piper usaran aceleracion GPU via CoreML."
    elif [[ "$COREML_STATUS" == "not_available" ]]; then
        echo -e "  ${YELLOW}[INFO]${NC} CoreML EP no disponible. Usando CPU."
        echo -e "  ${CYAN}[INFO]${NC} Para habilitar: reinstala onnxruntime con soporte CoreML."
    else
        echo -e "  ${YELLOW}[WARN]${NC} No se pudo verificar CoreML."
    fi
else
    echo -e "  ${YELLOW}[INFO]${NC} Arquitectura: ${ARCH} (no Apple Silicon)."
    echo -e "  ${CYAN}[INFO]${NC} GPU acceleration limitada en Intel Mac."
fi

# =============================================
# 6. Verificar voces Piper
# =============================================
echo ""
echo -e "${WHITE}[6/6] Voces Piper...${NC}"

mkdir -p models/piper

if ls models/piper/*.onnx &>/dev/null; then
    VOICE_COUNT=$(ls models/piper/*.onnx 2>/dev/null | wc -l | tr -d ' ')
    echo -e "  ${GREEN}[OK]${NC} ${VOICE_COUNT} voces encontradas."
else
    echo -e "  ${YELLOW}[INFO]${NC} Sin voces. Se descargaran automaticamente al usar Piper."
fi

# =============================================
# Resumen
# =============================================
echo ""
echo -e "${CYAN}===============================================${NC}"
echo -e "${GREEN}          INSTALACION COMPLETADA${NC}"
echo -e "${CYAN}===============================================${NC}"
echo ""

if [ "$NEED_REBOOT" -eq 1 ]; then
    echo -e "${YELLOW}[INFO]${NC} Entorno virtual creado. Si hay errores, cierra y vuelve a abrir la terminal."
fi

echo -e "  Para iniciar:  ${WHITE}./start.sh${NC}"
echo -e "  Para detener:  ${WHITE}./stop.sh${NC}"
echo -e "  Dashboard:     ${CYAN}http://localhost:9999${NC}"
echo ""
