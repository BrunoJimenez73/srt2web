# Matriz de Compatibilidad - SRT2Web

## Versiones Soportadas

| Componente | Versión Mínima | Versión Recomendada | Notas |
|------------|-----------------|----------------------|-------|
| **Sistema Operativo** | | | |
| Windows | 10 (64-bit) | 11 (64-bit) | Requiere PowerShell 5.1+ |
| macOS | 12 (Monterey) | 15 (Sequoia) | Requiere Homebrew para FFmpeg |
| Ubuntu/Debian | 20.04 LTS | 24.04 LTS | Requiere Python 3.12 |
| **Python** | 3.12.0 | 3.12.10 | NO usar 3.13+ (problemas con pydantic v1) |
| **Node.js** | 22.12.0 | 22.x LTS | Requiere npm 10+ |
| **FFmpeg** | 5.0 | 7.0 | Requiere soporte HLS (h264_mp4aac) |
| **CUDA** | 12.0 | 12.4 | Solo para TTS con GPU (Piper) |
| **cuDNN** | 8.9 | 9.0 | Instalar via `nvidia-cudnn-cu12` |
| **ONNX Runtime** | 1.17.0 | 1.20.0 | Requiere CUDA 12.x para GPU |
| **PyTorch** | 2.1.0 | 2.3.0 | Solo para Whisper (transcripción) |
| **MPS** | macOS 12+ | macOS 15+ | Solo para Apple Silicon (M1/M2/M3) |

## Hardware Recomendado

| Componente | Mínimo | Recomendado | Notas |
|------------|---------|--------------|-------|
| **CPU** | 4 núcleos | 8+ núcleos | Para procesamiento de video en tiempo real |
| **RAM** | 8 GB | 16+ GB | Video + modelos consumen memoria |
| **GPU** | Opcional | NVIDIA RTX 3060+ | Para TTS con Piper (CUDA) o Apple M1+ (MPS) |
| **Disco** | 5 GB libres | 20+ GB | Modelos Whisper (tiny~3GB, large~3GB) |

## Modelos Whisper Soportados

| Modelo | Tamaño | CPU (ms/chunk) | GPU (ms/chunk) | Notas |
|--------|---------|------------------|------------------|-------|
| tiny | 75 MB | ~500 | ~200 | Muy rápido, menor precisión |
| base | 140 MB | ~800 | ~300 | Balanceado |
| small | 460 MB | ~1500 | ~600 | Recomendado para calidad |
| medium | 1.5 GB | ~3000 | ~1200 | Alta calidad |
| large | 3 GB | ~6000 | ~2500 | Máxima calidad |

## Voces Piper TTS (Español)

| Voz | Calidad | Tamaño | Velocidad CPU | Notas |
|-----|--------|---------|--------------|-------|
| es_ES-sharvard-medium | Alta | 50 MB | ~50ms/chunk | Voz masculina, recomendada |
| es_ES-davefx-medium | Alta | 50 MB | ~50ms/chunk | Voz masculina alternativa |
| es_MX-claude-medium | Alta | 50 MB | ~50ms/chunk | Voz feminina (México) |
| es_AR-daniela-medium | Alta | 50 MB | ~50ms/chunk | Voz feminina (Argentina) |

## Navegadores Soportados

| Navegador | Versión Mínima | Notas |
|-----------|-----------------|-------|
| Chrome | 100+ | Soporte completo HLS |
| Firefox | 100+ | Soporte completo HLS |
| Edge | 100+ | Soporte completo HLS |
| Safari | 16+ | Native HLS (sin librería) |
| Opera | 90+ | Soporte completo HLS |

## Configuración Validada

| Entorno | OS | Python | Node | FFmpeg | CUDA | Estado |
|----------|----|--------|------|--------|------|--------|
| Desarrollo | Windows 11 | 3.12.10 | 22.12.0 | 7.0 | N/A | ✅ Tests passing |
| Producción | Ubuntu 24.04 | 3.12.10 | 22.x | 6.0 | 12.4 | ⏳ Por validar |
| Mac Silicon | macOS 15 | 3.12.10 | 22.x | 6.0 | MPS | ⏳ Por validar |

## Notas Importantes

1. **Python 3.13+ NO SOPORTADO**: argostranslate requiere pydantic v1 que tiene conflictos con Python 3.14
2. **CUDA 12.x REQUERIDO**: Piper TTS usa ONNX Runtime que requiere CUDA 12.x (NO 11.x)
3. **cuDNN 9.x INCOMPATIBLE**: ONNX Runtime NO soporta cuDNN 9.x (usar 8.9 via pip)
4. **FFmpeg en PATH**: Requiere que FFmpeg esté accesible via línea de comandos
5. **Modelos Whisper**: El modelo `large-v3` requiere ~3GB RAM adicional

## Verificación Rápida

```bash
# Verificar versiones
python --version          # Debe ser 3.12.x
node --version            # Debe ser 22.x
ffmpeg -version          # Debe ser 5.0+
nvidia-smi              # Verificar GPU y CUDA (opcional)

# Verificar dependencias Python
pip list | grep -E "torch|onnxruntime|argostranslate"

# Verificar FFmpeg codecs
ffmpeg -encoders 2>/dev/null | grep -E "h264_nvenc|h265_nvenc|aac|opus"

# Verificar modelos descargados
ls -lh models/whisper/     # Modelos Whisper
ls -lh models/piper/      # Voces Piper
```

## Troubleshooting

### Windows
- **Error: `python` no encontrado**: Instalar Python 3.12 desde python.org
- **Error: `ffmpeg` no encontrado**: Agregar FFmpeg al PATH
- **Error: `pip` no encontrado**: Re-instalar Python con "Add to PATH"

### macOS
- **Error: `brew` no encontrado**: Instalar Homebrew desde brew.sh
- **Error: MPS no disponible**: Usar solo Apple Silicon (M1/M2/M3)
- **Error: `pip` falla**: Usar `python -m pip` en lugar de `pip`

### Ubuntu/Debian
- **Error: `python3` no encontrado**: `sudo apt install python3.12`
- **Error: `ffmpeg` no encontrado**: `sudo apt install ffmpeg`
- **Error: CUDA no disponible**: Instalar NVIDIA drivers + CUDA Toolkit 12.x

---

**Última actualización**: 2026-05-03
**Versión SRT2Web**: 0.6.8

