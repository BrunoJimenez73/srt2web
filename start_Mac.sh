#!/bin/bash
# SRT2Web - Script de inicio para Mac Silicon
# Funciona en Mac M1/M2/M3 con macOS 12+

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "==============================================="
echo "         SRT2Web - INICIANDO"
echo "==============================================="
echo ""

# =============================================
# 1. Verificar entorno virtual
# =============================================
if [ ! -d "venv" ]; then
    echo -e "${RED} ✗ Entorno virtual no encontrado${NC}"
    echo ""
    echo " Ejecuta primero: ./install_Mac.sh"
    echo ""
    exit 1
fi

# Activar entorno virtual
source venv/bin/activate

# =============================================
# 2. Configurar variables de entorno para Mac Silicon
# =============================================
export PYTHONPATH="$SCRIPT_DIR"

# Configuración para MPS (Metal Performance Shaders)
# Mejorar uso de memoria en GPU Apple Silicon
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

# Configuración para ONNX Runtime con CoreML
export COREML_ENABLE_PROFILING=0

# =============================================
# 3. Verificar dependencias
# =============================================
echo -e "${BLUE}[1/4] Verificando dependencias...${NC}"

# Verificar FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW} ⚠️  FFmpeg no encontrado en PATH${NC}"
    echo -e "${YELLOW}       Algunas funcionalidades pueden no estar disponibles${NC}"
fi

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW} ⚠️  Node.js no encontrado en PATH${NC}"
    echo -e "${YELLOW}       El frontend no podrá ser reconstruido${NC}"
fi

echo -e "${GREEN} ✓ Dependencias verificadas${NC}"

# =============================================
# 4. Verificar/Crear archivo de configuración
# =============================================
echo ""
echo -e "${BLUE}[2/4] Verificando configuración...${NC}"

if [ ! -f "config.yaml" ]; then
    echo -e "${BLUE} Creando config.yaml por defecto...${NC}"
    cp config/config.yaml config.yaml 2>/dev/null || echo "version: '0.6.2'" > config.yaml
    echo -e "${GREEN} ✓ Configuración creada${NC}"
fi

# =============================================
# 5. Verificar/Construir frontend
# =============================================
echo ""
echo -e "${BLUE}[3/4] Verificando frontend...${NC}"

if [ ! -d "server/static" ] || [ ! -f "server/static/index.html" ]; then
    echo -e "${BLUE} Construyendo frontend...${NC}"
    
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        cd frontend
        
        # Instalar dependencias si es necesario
        if [ ! -d "node_modules" ]; then
            echo -e "${BLUE} Instalando dependencias de frontend...${NC}"
            npm install --silent
        fi
        
        # Construir
        echo -e "${BLUE} Construyendo frontend...${NC}"
        npm run build:local --silent
        
        cd ..
        echo -e "${GREEN} ✓ Frontend construido${NC}"
    else
        echo -e "${YELLOW} ⚠️  Frontend no encontrado. El servidor iniciará sin UI.${NC}"
    fi
else
    echo -e "${GREEN} ✓ Frontend ya construido${NC}"
fi

# =============================================
# 6. Mostrar información del sistema
# =============================================
echo ""
echo -e "${BLUE}[4/4] Información del sistema...${NC}"

# Arquitectura
echo -e "  Arquitectura: $(uname -m)"

# Versión de macOS
echo -e "  macOS: $(sw_vers -productVersion)"

# GPU
python -c "
import torch
if torch.backends.mps.is_available():
    print('  GPU: Apple Silicon (MPS)')
elif torch.cuda.is_available():
    print('  GPU: CUDA')
else:
    print('  GPU: CPU (sin aceleración GPU)')
" 2>/dev/null

echo ""

# =============================================
# 7. Iniciar servidor
# =============================================
echo "==============================================="
echo "         INICIANDO SERVIDOR"
echo "==============================================="
echo ""
echo -e "${GREEN}→ Servidor: http://127.0.0.1:9999${NC}"
echo -e "${GREEN}→ Player:  http://127.0.0.1:9999/player${NC}"
echo -e "${GREEN}→ Docs:    http://127.0.0.1:9999/docs${NC}"
echo ""
echo -e "${YELLOW}Para detener: Ctrl+C${NC}"
echo ""

# Iniciar servidor
python main.py --host 127.0.0.1 --port 9999