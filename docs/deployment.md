# Guía de Despliegue - SRT2Web

## Requisitos del Sistema

### Requisitos Mínimos

| Componente | Requisito |
|------------|-----------|
| **CPU** | 4 núcleos minimum |
| **RAM** | 8 GB |
| **GPU** | NVIDIA CUDA (opcional, para aceleración) |
| **SO** | Windows 10/11, macOS 12+, Linux |
| **Python** | 3.12 |
| **FFmpeg** | 6.0+ |

### Requisitos Recomendados

| Componente | Recomendado |
|------------|------------|
| **CPU** | 8+ núcleos |
| **RAM** | 16 GB+ |
| **GPU** | NVIDIA RTX 3060+ con CUDA 12.x |
| **Almacenamiento** | 10 GB libres |

## Instalación en Windows

### 1. Clonar Repositorio

```bash
git clone https://github.com/BrunoJimenez73/srt2web.git
cd srt2web
```

### 2. Crear Entorno Virtual

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar FFmpeg

Descarga desde [ffmpeg.org](https://ffmpeg.org/download.html) o usa:

```powershell
winget install ffmpeg
```

### 5. Configurar CUDA (Opcional)

```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

### 6. Ejecutar Servidor

```bash
start.bat
```

El servidor estará disponible en `http://localhost:9999`

## Instalación en Mac Silicon

### 1. Ejecutar Script de Instalación

```bash
chmod +x install_Mac.sh
./install_Mac.sh
```

### 2. Verificar Dependencias

```bash
python scripts/check_mac_deps.py
```

### 3. Iniciar Servidor

```bash
./start_Mac.sh
```

## Configuración de OBS para SRT

### Configuración de Salida

1. Abre OBS Studio
2. Ve a **Configuración → Transmisión**
3. Selecciona **SRT** como tipo de servicio
4. Configura:
   - **Dirección**: `127.0.0.1`
   - **Puerto**: `9000`
   - **Latency**: `120` ms (mínimo recomendado)

### Configuración de Salida de Video

En **Configuración → Salida**:

| Parámetro | Valor |
|-----------|-------|
| Codificador | H.264 (NVIDIA NVENC si disponible) |
| Tasa de bits | 4000-8000 Kbps |
| Intervalo de keyframes | 10 segundos |

### Intervalo de Keyframes

**Importante**: El intervalo de keyframes debe ser **múltiplo de 10 segundos** para que coincida con la configuración de chunks de SRT2Web:

```
chunk_duration_sec = 10
```

Si el intervalo es 2s,会导致 problemas de sincronización.

## Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `SRT2WEB_HOST` | Host del servidor | `127.0.0.1` |
| `SRT2WEB_PORT` | Puerto del servidor | `9999` |
| `SRT2WEB_AUTH_TOKEN` | Token de autenticación | (ninguno) |
| `CUDA_VISIBLE_DEVICES` | GPUs a usar | `0` |
| `PYTORCH_CUDA_ALLOC_CONF` | Configuración memoria GPU | `max_split_size_mb:512` |

## Configuración de Producción

### Archivo config.yaml

```yaml
server:
  host: "0.0.0.0"
  port: 9999
  auth_token: "tu-token-seguro-aqui"

input:
  chunk_duration_sec: 10
  buffer_size: 3

output:
  web:
    segment_duration: 10
    list_size: 6

transcriber:
  model: "medium"
  device: "cuda"
  beam_size: 2

tts:
  engine: "piper"
  voice: "en_US-ryan-low"
  device: "cuda"
  speed: 1.3
```

### Optimizaciones de Rendimiento

1. **GPU**: Usar CUDA para transcripción y TTS
2. **Audio Mixing**: Ya optimizado con numpy (no FFmpeg)
3. **FFmpeg Pool**: Máximo 4 procesos simultáneos
4. **Segmentos HLS**: 10s duración, 6 segmentos en lista

## Troubleshooting

### Error: "CUDA not available"

```bash
# Verificar instalación CUDA
python scripts/test_cuda.py

# Reinstalar dependencias NVIDIA
pip uninstall nvidia-cublas-cu12 nvidia-cudnn-cu12 -y
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

### Error: "No input video chunk"

- Verifica que OBS esté transmitiendo
- Verifica que el intervalo de keyframes sea múltiplo de 10s
- Verifica que el puerto SRT (9000) esté abierto

### Error: "Piper TTS blocked event loop"

- El loader usa subprocess para evitar bloqueo
- Timeout configurado en 90 segundos
- Ver logs en `logs/srt2web.log`

### Error: "Port already in use"

```bash
# Windows
netstat -ano | findstr :9999
taskkill /PID <pid> /F

# Linux/Mac
lsof -i :9999
kill -9 <pid>
```

## Docker

### Build Imagen

```bash
docker build -t srt2web:latest .
```

### Ejecutar Contenedor

```bash
docker run -p 9999:9999 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/logs:/app/logs \
  -e CUDA_VISIBLE_DEVICES=0 \
  srt2web:latest
```

## Verificación Post-Instalación

```bash
# Verificar estado de módulos
curl http://localhost:9999/api/status

# Verificar WebSocket
curl -I http://localhost:9999/ws/logs

# Verificar acceso al dashboard
curl http://localhost:9999/
```

## Estructura de Logs

```
logs/
├── srt2web.log      # Log principal (rotación 10MB)
├── srt2web.log.1    # Backup 1
├── srt2web.log.2    # Backup 2
└── srt2web.log.3    # Backup 3
```

## Monitoreo

### Endpoints de Estado

- `GET /api/status` - Estado del pipeline
- `GET /api/config` - Configuración actual
- `GET /api/metrics` - Métricas de GPU y sistema

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:9999/ws/logs?token=TU_TOKEN');
ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(log.timestamp, log.level, log.message);
};
```

## Checklist de Despliegue

- [ ] Python 3.12 instalado
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] FFmpeg instalado y en PATH
- [ ] CUDA configurado (si GPU disponible)
- [ ] Config.yaml personalizado
- [ ] Puerto 9999 disponible
- [ ] OBS configurado con SRT
- [ ] Servidor iniciado (`start.bat`)
- [ ] Dashboard accesible en `http://localhost:9999`
- [ ] Logs verificables en `logs/srt2web.log`