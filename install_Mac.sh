#!/bin/bash
# SRT2Web - Instalador para Mac Silicon (ARM64)
# Funciona en Mac M1/M2/M3 con macOS 12+

set -e  # Salir si hay error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "==============================================="
echo "         SRT2Web - INSTALADOR MAC"
echo "==============================================="
echo ""

# =============================================
# 0. Verificar arquitectura
# =============================================
echo -e "${BLUE}[0/8] Verificando arquitectura...${NC}"

ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    echo -e "${YELLOW}⚠️  Advertencia: Este script está optimizado para Mac Silicon (ARM64)${NC}"
    echo -e "${YELLOW}   Arquitectura detectada: $ARCH${NC}"
    echo -e "${YELLOW}   Para Mac Intel, considera usar Docker o instalar dependencias manualmente${NC}"
    echo ""
fi

# =============================================
# 1. Verificar/Instalar Homebrew (opcional)
# =============================================
echo -e "${BLUE}[1/8] Verificando Homebrew...${NC}"

if command -v brew &> /dev/null; then
    echo -e "${GREEN} ✓ Homebrew ya instalado${NC}"
    BREW_INSTALLED=1
else
    echo -e "${YELLOW} ⚠️  Homebrew no encontrado${NC}"
    echo ""
    echo " Homebrew es recomendado pero no obligatorio."
    echo " Sin Homebrew, necesitarás instalar Python, Node.js y FFmpeg manualmente."
    echo ""
    read -p "¿Instalar Homebrew ahora? (s/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo -e "${BLUE} Instalando Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Agregar Homebrew al PATH para Apple Silicon
        if [ "$ARCH" = "arm64" ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        fi
        
        echo -e "${GREEN} ✓ Homebrew instalado${NC}"
        BREW_INSTALLED=1
    else
        echo -e "${YELLOW} ⚠️  Homebrew no instalado. Continuando sin él.${NC}"
        BREW_INSTALLED=0
    fi
fi

# =============================================
# 2. Instalar dependencias del sistema (si hay Homebrew)
# =============================================
if [ $BREW_INSTALLED -eq 1 ]; then
    echo ""
    echo -e "${BLUE}[2/8] Instalando dependencias del sistema...${NC}"
    
    # Verificar si FFmpeg ya está instalado
    if command -v ffmpeg &> /dev/null; then
        echo -e "${GREEN} ✓ FFmpeg ya instalado${NC}"
    else
        echo -e "${BLUE} Instalando FFmpeg...${NC}"
        brew install ffmpeg
        echo -e "${GREEN} ✓ FFmpeg instalado${NC}"
    fi
    
    # Verificar si Node.js ya está instalado
    if command -v node &> /dev/null; then
        echo -e "${GREEN} ✓ Node.js ya instalado ($(node --version))${NC}"
    else
        echo -e "${BLUE} Instalando Node.js...${NC}"
        brew install node
        echo -e "${GREEN} ✓ Node.js instalado${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}[2/8] Saltando instalación de dependencias (sin Homebrew)${NC}"
    echo -e "${YELLOW}       Asegúrate de tener Python 3.12, Node.js y FFmpeg instalados${NC}"
fi

# =============================================
# 3. Crear/Verificar entorno virtual
# =============================================
echo ""
echo -e "${BLUE}[3/8] Entorno virtual Python...${NC}"

PYTHON_CMD=""

# Buscar Python 3.12
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    if [[ $PYTHON_VERSION == 3.12* ]]; then
        PYTHON_CMD="python3"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED} ✗ Python 3.12 no encontrado${NC}"
    echo ""
    echo " Instala Python 3.12:"
    echo "   - Desde python.org: https://www.python.org/downloads/release/python-3120/"
    echo "   - O con Homebrew: brew install python@3.12"
    echo ""
    exit 1
fi

if [ ! -d "venv" ]; then
    echo -e "${BLUE} Creando entorno virtual con $PYTHON_CMD...${NC}"
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN} ✓ Entorno virtual creado${NC}"
else
    echo -e "${GREEN} ✓ Entorno virtual ya existe${NC}"
fi

# Activar entorno virtual
source venv/bin/activate

# =============================================
# 4. Instalar dependencias Python
# =============================================
echo ""
echo -e "${BLUE}[4/8] Instalando dependencias Python...${NC}"

# Actualizar pip
python -m pip install --upgrade pip wheel setuptools --quiet

# Instalar dependencias del proyecto
echo -e "${BLUE} Instalando dependencias del proyecto...${NC}"
python -m pip install -r config/requirements.txt --quiet 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN} ✓ Dependencias instaladas${NC}"
else
    echo -e "${YELLOW} ⚠️  Error instalando dependencias. Verifica requirements.txt${NC}"
fi

# =============================================
# 5. Instalar PyTorch con MPS (Metal Performance Shaders)
# =============================================
echo ""
echo -e "${BLUE}[5/8] PyTorch con MPS (GPU Apple Silicon)...${NC}"

# Verificar si PyTorch ya tiene soporte MPS
MPS_AVAILABLE=$(python -c "import torch; print('MPS' if torch.backends.mps.is_available() else 'CPU')" 2>/dev/null || echo "CPU")

if [ "$MPS_AVAILABLE" = "MPS" ]; then
    echo -e "${GREEN} ✓ PyTorch con MPS ya disponible${NC}"
else
    echo -e "${BLUE} Instalando PyTorch con soporte MPS...${NC}"
    python -m pip install torch torchvision torchaudio --quiet 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN} ✓ PyTorch instalado${NC}"
    else
        echo -e "${YELLOW} ⚠️  Fallback a PyTorch CPU${NC}"
        python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet 2>/dev/null
    fi
fi

# =============================================
# 6. Instalar ONNX Runtime
# =============================================
echo ""
echo -e "${BLUE}[6/8] ONNX Runtime...${NC}"

# Verificar si ONNX Runtime GPU está disponible
ONNX_STATUS=$(python -c "import onnxruntime as ort; print('CoreML' if 'CoreMLExecutionProvider' in ort.get_available_providers() else 'CPU')" 2>/dev/null || echo "CPU")

if [ "$ONNX_STATUS" = "CoreML" ]; then
    echo -e "${GREEN} ✓ ONNX Runtime con CoreML ya disponible${NC}"
else
    echo -e "${BLUE} Instalando onnxruntime-silicon para CoreML...${NC}"
    python -m pip install onnxruntime-silicon --quiet 2>/dev/null || \
    python -m pip install onnxruntime --quiet 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN} ✓ ONNX Runtime instalado${NC}"
    else
        echo -e "${YELLOW} ⚠️  Fallback a CPU${NC}"
    fi
fi

# =============================================
# 7. Descargar modelos Whisper
# =============================================
echo ""
echo -e "${BLUE}[7/8] Modelos Whisper...${NC}"

WHISPER_CACHE=".cache/srt2web/whisper"
if [ ! -d "$WHISPER_CACHE/models--Systran--faster-whisper-tiny" ]; then
    echo -e "${BLUE} Descargando modelo Whisper tiny...${NC}"
    python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', download_root='$WHISPER_CACHE')" 2>/dev/null
    
    if [ -d "$WHISPER_CACHE/models--Systran--faster-whisper-tiny" ]; then
        echo -e "${GREEN} ✓ Modelo Whisper tiny descargado${NC}"
    else
        echo -e "${YELLOW} ⚠️  No se pudo descargar. Se descargará al usar.${NC}"
    fi
else
    echo -e "${GREEN} ✓ Modelo Whisper tiny ya existe${NC}"
fi

# =============================================
# 8. Verificar voces Piper
# =============================================
echo ""
echo -e "${BLUE}[8/8] Voces Piper...${NC}"

if [ ! -d "models/piper" ]; then
    mkdir -p models/piper
fi

echo -e "${BLUE} Verificando voces Piper...${NC}"
python scripts/download_piper_voices.py 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN} ✓ Voces verificadas${NC}"
else
    echo -e "${YELLOW} ⚠️  Se descargará al usar Piper${NC}"
fi

# =============================================
# Resumen
# =============================================
echo ""
echo "==============================================="
echo "           RESUMEN DE INSTALACIÓN"
echo "==============================================="
echo ""

# PyTorch status
python -c "
import torch
if torch.backends.mps.is_available():
    print('PyTorch: MPS (Apple Silicon GPU)')
elif torch.cuda.is_available():
    print('PyTorch: CUDA')
else:
    print('PyTorch: CPU')
" 2>/dev/null || echo "PyTorch: No verificado"

# ONNX status
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

# FFmpeg status
if command -v ffmpeg &> /dev/null; then
    FFMPEG_ENCODERS=$(ffmpeg -encoders 2>/dev/null | grep -c "h264_videotoolbox" || echo "0")
    if [ "$FFMPEG_ENCODERS" -gt 0 ]; then
        echo "FFmpeg: OK (VideoToolbox - Hardware Acceleration)"
    else
        echo "FFmpeg: OK (Software encoding)"
    fi
else
    echo "FFmpeg: No encontrado"
fi

echo ""
echo "==============================================="
echo "         INSTALACIÓN COMPLETADA"
echo "==============================================="
echo ""
echo " Para iniciar el servidor:"
echo "   ./start_Mac.sh"
echo ""
echo " Para detener el servidor:"
echo "   ./stop_Mac.sh"
echo ""

# Hacer scripts ejecutables
chmod +x start_Mac.sh stop_Mac.sh 2>/dev/null || true