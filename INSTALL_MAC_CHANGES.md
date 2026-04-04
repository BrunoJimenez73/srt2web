# Cambios Realizados a install_Mac.sh

## Resumen
Se ha actualizado el script `install_Mac.sh` para garantizar una instalación correcta de **Uvicorn** y todas las dependencias necesarias para Mac Silicon (M1/M2/M3), incluyendo la creación de un archivo de requisitos específico para Mac.

## Problemas Corregidos

### 1. **Error con onnxruntime-gpu en Mac Silicon**
- **Problema**: `requirements.txt` incluía `onnxruntime-gpu>=1.19.0` que NO está disponible para Mac Silicon (el paquete solo existe para NVIDIA GPUs)
- **Solución**:
  - Creado `config/requirements_mac.txt` específico para Mac Silicon
  - Eliminado `onnxruntime-gpu` del requirements de Mac (no existe para ARM64)
  - El script usa automáticamente `requirements_mac.txt` si está disponible
  - ONNX Runtime se instala por separado en la sección 6 con `onnxruntime-silicon` o `onnxruntime` estándar

### 2. **Instalación de Uvicorn**
- **Problema**: El script usaba banderas `--quiet` que ocultaban errores de instalación
- **Solución**: 
  - Eliminadas las banderas `--quiet` para mostrar el progreso real
  - Agregada verificación explícita de Uvicorn después de la instalación
  - Si Uvicorn falla, se intenta instalar manualmente con fallback

### 3. **Verificación de Dependencias Críticas**
- **Problema**: No se verificaba si las dependencias se instalaron correctamente
- **Solución**:
  - Verificación de versión de Uvicorn: `python -c "import uvicorn; print('  Uvicorn version:', uvicorn.__version__)"`
  - Verificación de MPS (Metal Performance Shaders) después de instalar PyTorch
  - Verificación de CoreML Execution Provider después de instalar ONNX Runtime

### 4. **Mejoras en la Instalación de PyTorch**
- **Problema**: No se verificaba si MPS estaba activado después de instalar
- **Solución**:
  - Verificación post-instalación de MPS
  - Mensaje claro cuando MPS está activado: `✓ MPS (Metal Performance Shaders) activado`
  - Fallback automático a CPU si MPS no está disponible

### 5. **Mejoras en la Instalación de ONNX Runtime**
- **Problema**: No se verificaba si CoreML estaba disponible
- **Solución**:
  - Intenta instalar `onnxruntime-silicon` primero (optimizado para Apple Silicon)
  - Fallback a `onnxruntime` estándar si no está disponible
  - Verificación post-instalación de CoreML Execution Provider
  - Mensaje claro del estado: `✓ CoreML Execution Provider activado` o `⚠️ Usando CPU (CoreML no disponible)`

## Archivo Creado: config/requirements_mac.txt

Se ha creado un archivo de requisitos específico para Mac Silicon que:
- **NO incluye** `onnxruntime-gpu` (no disponible para Mac)
- Incluye todas las demás dependencias necesarias
- Es usado automáticamente por `install_Mac.sh`

```
# SRT2Web - Modular SRT Stream Processor (Mac Silicon)
# Core
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pyyaml>=6.0
aiofiles>=23.0
websockets>=12.0
numpy>=1.24.0
pydub>=0.25.1
psutil>=5.9.0
nvidia-ml-py>=12.0.0

# Phase 2 - Processing
faster-whisper>=1.0.0
argostranslate>=1.9.0
piper-tts>=1.2.0

# GPU Support for Mac Silicon (CoreML via onnxruntime-silicon)
# NOTA: onnxruntime-gpu no está disponible para Mac Silicon
# Se instala onnxruntime-silicon o onnxruntime estándar en el script install_Mac.sh

# TTS Engines
edge-tts>=6.1.0
```

## Cambios Detallados en install_Mac.sh

### Sección 4: Instalación de Dependencias Python
```bash
# ANTES:
python -m pip install -r config/requirements.txt --quiet 2>/dev/null

# AHORA:
# Usar requirements_mac.txt que no incluye onnxruntime-gpu (no disponible para Mac)
if [ -f "config/requirements_mac.txt" ]; then
    echo -e "${BLUE} Usando config/requirements_mac.txt (optimizado para Mac Silicon)...${NC}"
    python -m pip install -r config/requirements_mac.txt
else
    echo -e "${YELLOW} ⚠️  No se encontró requirements_mac.txt, usando requirements.txt...${NC}"
    python -m pip install -r config/requirements.txt
fi

# Verificación explícita de Uvicorn
python -c "import uvicorn; print('  Uvicorn version:', uvicorn.__version__)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED} ✗ Uvicorn no se instaló correctamente${NC}"
    echo -e "${BLUE} Intentando instalar Uvicorn manualmente...${NC}"
    python -m pip install "uvicorn[standard]>=0.24.0"
    if [ $? -ne 0 ]; then
        echo -e "${RED} ✗ No se pudo instalar Uvicorn${NC}"
        exit 1
    fi
fi
echo -e "${GREEN} ✓ Uvicorn verificado${NC}"
```

### Sección 5: PyTorch con MPS
```bash
python -m pip install torch torchvision torchaudio

if [ $? -eq 0 ]; then
    echo -e "${GREEN} ✓ PyTorch instalado${NC}"
    # Verificar MPS después de instalar
    MPS_AVAILABLE=$(python -c "import torch; print('MPS' if torch.backends.mps.is_available() else 'CPU')" 2>/dev/null || echo "CPU")
    if [ "$MPS_AVAILABLE" = "MPS" ]; then
        echo -e "${GREEN} ✓ MPS (Metal Performance Shaders) activado${NC}"
    fi
fi
```

### Sección 6: ONNX Runtime
```bash
python -m pip install onnxruntime-silicon
if [ $? -ne 0 ]; then
    echo -e "${YELLOW} ⚠️  onnxruntime-silicon no disponible, instalando onnxruntime estándar...${NC}"
    python -m pip install onnxruntime
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN} ✓ ONNX Runtime instalado${NC}"
    # Verificar CoreML después de instalar
    ONNX_STATUS=$(python -c "import onnxruntime as ort; print('CoreML' if 'CoreMLExecutionProvider' in ort.get_available_providers() else 'CPU')" 2>/dev/null || echo "CPU")
    if [ "$ONNX_STATUS" = "CoreML" ]; then
        echo -e "${GREEN} ✓ CoreML Execution Provider activado${NC}"
    else
        echo -e "${YELLOW} ⚠️  Usando CPU (CoreML no disponible)${NC}"
    fi
fi
```

## Beneficios

1. **Compatibilidad Mac Silicon**: Ya no hay errores con `onnxruntime-gpu` en Mac
2. **Transparencia**: Ahora puedes ver exactamente qué se está instalando y si hay errores
3. **Confiabilidad**: Verificaciones explícitas garantizan que Uvicorn y otras dependencias críticas estén instaladas
4. **Debugging**: Si algo falla, verás el error completo en lugar de un mensaje genérico
5. **Optimización**: El script verifica y activa automáticamente las optimizaciones de GPU (MPS/CoreML) cuando están disponibles

## Cómo Usar

```bash
# 1. Hacer el script ejecutable (si no lo es)
chmod +x install_Mac.sh

# 2. Ejecutar el instalador
./install_Mac.sh

# 3. Verificar instalación
./start_Mac.sh
```

## Dependencias Instaladas

El script instala automáticamente:

### Del archivo `config/requirements_mac.txt`:
- **FastAPI** >= 0.104.0 - Framework web asíncrono
- **Uvicorn**[standard] >= 0.24.0 - Servidor ASGI (¡AHORA VERIFICADO!)
- **PyYAML** >= 6.0 - Manejo de configuración
- **aiofiles** >= 23.0 - Operaciones de archivo asíncronas
- **websockets** >= 12.0 - Soporte WebSocket
- **numpy** >= 1.24.0 - Operaciones numéricas
- **pydub** >= 0.25.1 - Procesamiento de audio
- **psutil** >= 5.9.0 - Información del sistema
- **nvidia-ml-py** >= 12.0.0 - Monitoreo GPU (para NVIDIA, opcional en Mac)
- **faster-whisper** >= 1.0.0 - Transcripción de audio
- **argostranslate** >= 1.9.0 - Traducción automática
- **piper-tts** >= 1.2.0 - Síntesis de voz
- **edge-tts** >= 6.1.0 - TTS alternativo

### GPU Support (Apple Silicon) - Instalado por separado:
- **PyTorch** con MPS (Metal Performance Shaders) - Aceleración GPU
- **ONNX Runtime** con CoreML - Aceleración GPU para modelos ONNX

### Sistema (vía Homebrew):
- **FFmpeg** - Procesamiento de video/audio
- **Node.js** - Construcción del frontend

## Verificación Post-Instalación

Después de ejecutar `install_Mac.sh`, el script muestra un resumen con:

```
===============================================
           RESUMEN DE INSTALACIÓN
===============================================

PyTorch: MPS (Apple Silicon GPU)
ONNX: CoreML (Apple Silicon GPU)
FFmpeg: OK (VideoToolbox - Hardware Acceleration)

===============================================
         INSTALACIÓN COMPLETADA
===============================================

 Para iniciar el servidor:
   ./start_Mac.sh

 Para detener el servidor:
   ./stop_Mac.sh
```

## Solución de Problemas

### Error: "Could not find a version that satisfies the requirement onnxruntime-gpu"
**Causa**: Estás usando `requirements.txt` en lugar de `requirements_mac.txt`
**Solución**: El script ahora usa automáticamente `requirements_mac.txt`. Si el error persiste, asegúrate de que el archivo `config/requirements_mac.txt` exista.

### Si Uvicorn falla al instalar:
El script intentará instalar manualmente con:
```bash
python -m pip install "uvicorn[standard]>=0.24.0"
```

### Si MPS no está disponible:
PyTorch se instalará en modo CPU automáticamente.

### Si CoreML no está disponible:
ONNX Runtime funcionará en modo CPU.

### Si hay errores de permisos:
```bash
chmod +x install_Mac.sh
./install_Mac.sh
```

## Notas Importantes

1. **Python 3.12**: El script requiere Python 3.12 específicamente
2. **Homebrew**: Es recomendado pero no obligatorio
3. **Entorno Virtual**: Se crea automáticamente en la carpeta `venv/`
4. **GPU Acceleration**: MPS y CoreML se activan automáticamente si están disponibles
5. **onnxruntime-gpu**: NO está disponible para Mac Silicon, se usa `onnxruntime-silicon` o `onnxruntime` estándar

## Archivos Relacionados

- `install_Mac.sh` - Script de instalación (ACTUALIZADO)
- `start_Mac.sh` - Script de inicio del servidor
- `stop_Mac.sh` - Script de parada del servidor
- `config/requirements.txt` - Dependencias del proyecto (para Windows/Linux con NVIDIA)
- `config/requirements_mac.txt` - Dependencias para Mac Silicon (NUEVO)