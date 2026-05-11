# Guía de Despliegue - SRT2Web

## Requisitos del Sistema

### Requisitos Mínimos

| Componente  | Requisito                                |
| ----------- | ---------------------------------------- |
| **CPU**     | 4 núcleos minimum                        |
| **RAM**     | 8 GB                                     |
| **GPU**     | NVIDIA CUDA (opcional, para aceleración) |
| **SO**      | Windows 10/11, macOS 12+, Linux          |
| **Python**  | 3.12+                                    |
| **FFmpeg**  | 6.0+                                     |
| **Node.js** | 18+ (para build frontend)                |

### Requisitos Recomendados

| Componente         | Recomendado                    |
| ------------------ | ------------------------------ |
| **CPU**            | 8+ núcleos                     |
| **RAM**            | 16 GB+                         |
| **GPU**            | NVIDIA RTX 3060+ con CUDA 12.x |
| **Almacenamiento** | 10 GB libres                   |

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
pip install -r config/requirements.txt
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

### 6. Instalar Modelos Whisper

```bash
# Descargar modelo (ejemplo: tiny, base, small, medium, large)
python -c "import whisper; whisper.load_model('tiny')"
```

### 7. Ejecutar Servidor

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

Mac Silicon usa **MPS** (Metal Performance Shaders) para PyTorch y **CoreML** para ONNX Runtime.

## Configuración de OBS para SRT

### Configuración de Salida

1. Abre OBS Studio
2. Ve a **Configuración → Transmisión**
3. Selecciona **SRT** como tipo de servicio
4. Configura:
   - **Dirección**: `127.0.0.1`
   - **Puerto**: `9000`
   - **Latency**: `200` ms (recomendado)

### Configuración de Salida de Video

En **Configuración → Salida**:

| Parámetro                  | Valor                              |
| -------------------------- | ---------------------------------- |
| Codificador                | H.264 (NVIDIA NVENC si disponible) |
| Tasa de bits               | 4000-8000 Kbps                     |
| **Intervalo de keyframes** | **10 segundos** (crítico)          |

### Intervalo de Keyframes

**Importante**: El intervalo de keyframes debe ser **10 segundos** para que coincida con la configuración de chunks de SRT2Web. Valores diferentes causan problemas de sincronización "No input video chunk".

## Variables de Entorno

| Variable                           | Descripción               | Default                 |
| ---------------------------------- | ------------------------- | ----------------------- |
| `SRT2WEB_HOST`                     | Host del servidor         | `127.0.0.1`             |
| `SRT2WEB_PORT`                     | Puerto del servidor       | `9999`                  |
| `SRT2WEB_AUTH_TOKEN`               | Token de autenticación    | (ninguno)               |
| `CUDA_VISIBLE_DEVICES`             | GPUs a usar               | `0`                     |
| `PYTORCH_CUDA_ALLOC_CONF`          | Configuración memoria GPU | `max_split_size_mb:512` |
| `PYTORCH_MPS_HIGH_WATERMARK_RATIO` | Memory ratio MPS (Mac)    | `0.0`                   |

## Configuración Completa de config.yaml

```yaml
server:
  host: "127.0.0.1"
  port: 9999
  auth_token: "" # Token para proteger API/WebSocket
  rate_limit_rpm: 600 # Requests por minuto
  max_request_size_mb: 100 # Tamaño máximo de request

# Fuente de entrada
input:
  type: srt # srt | rtmp | file
  srt:
    listen_port: 9000
    mode: listener # listener | caller
    latency_ms: 200
    chunk_duration_sec: 15 # Duración chunks (segundos)
  rtmp:
    listen_port: 1935
    app: live
    stream_key: stream
    mode: listener
    chunk_duration_sec: 15
  file:
    path: "" # Ruta al archivo de video
    loop: false
    speed: 1.0
    chunk_duration_sec: 15

# Salida principal
output:
  type: web # web | rtmp | srt | webrtc | recording
  web:
    segment_duration: 4
    list_size: 6
    audio_offset_ms: 0
    encoder_mode: auto # auto | cpu | gpu
  rtmp:
    url: "rtmp://localhost/live/stream"
    video_bitrate: "2500k"
    audio_bitrate: "128k"
    video_codec: h264
    encoder_mode: auto
  srt:
    url: "srt://localhost:9001"
    mode: caller
    latency_ms: 200
    video_bitrate: "2500k"
    audio_bitrate: "128k"
  recording:
    output_path: "./output/recording.mp4"
    format: mp4
    codec: copy # copy | h264_nvenc | libx264
    quality_mode: cbr # cbr | crf
    video_crf: 23
    audio_codec: aac
    audio_bitrate: "128k"
    split_mode: none # none | time | size
    split_value: 600 # segundos o MB
    subtitles: burnt # none | burnt | track | vtt
    video_preset: fast

# Salidas múltiples simultáneas
outputs:
  - name: web_1
    type: web
    enabled: true
    config:
      segment_duration: 4
      list_size: 6
  - name: recording_1
    type: recording
    enabled: true
    config:
      output_path: "./output/grabacion.mp4"
      codec: copy
      subtitles: track # Subtítulos como pista separada

# Pipeline
pipeline:
  chunk_duration_sec: 15
  mode: thread_parallel # sequential | thread_parallel | async
  max_concurrent_chunks: 4
  buffer_size: 2
  retry_attempts: 2
  retry_delay: 1.0

# Módulos
modules:
  audio_extractor:
    enabled: true
  transcriber:
    enabled: true
    model: tiny # tiny | base | small | medium | large
    language: en
    device: cuda # auto | cuda | cpu | mps
    beam_size: 2
  translator:
    enabled: true
    source_lang: en
    target_lang: es
  subtitle_generator:
    enabled: true
    format: vtt # vtt | srt
    use_translated: true
    chunk_duration: 15
  tts_engine:
    enabled: true
    engine: piper # piper | edge-tts
    voice: es_AR-daniela-high
    speed: 1.2
    device: auto # auto | cuda | cpu
  audio_mixer:
    enabled: true
    original_volume: 0.8 # Ducking audio original
    tts_volume: 1.0
  video_muxer:
    enabled: true
    engine: hls # hls | webrtc
    hls_segment_duration: 4
    hls_list_size: 6
    encoder_mode: auto # auto | cpu | gpu
    video_quality: medium # fast | medium | slow
    video_crf: 18
    audio_codec: aac
    audio_bitrate: "64k"

    gpu_preset: p7 # p1-p7 (NVIDIA)
    video_preset: medium # ultrafast a veryslow
```

## Salida WebRTC

Para habilitar WebRTC, necesitas **MediaMTX** (rtsp-simple-server):

1. Descarga MediaMTX desde [github.com/bluenviron/mediamtx](https://github.com/bluenviron/mediamtx)
2. Configura en `config.yaml`:

```yaml
modules:
  video_muxer:
    engine: webrtc
    video_codec: h264
    audio_codec: opus
    audio_sample_rate: 48000
    video_bitrate: "2500k"
    video_fps: 30
    video_width: 1280
    video_height: 720
```

3. Accede al player en `http://localhost:9999/webrtc-player`

## CLI - Herramienta de Línea de Comandos

```bash
# Estado del pipeline
srt2web status
srt2web status --watch        # Modo observación continua

# Control del pipeline
srt2web start
srt2web stop
srt2web restart

# Configuración
srt2web config get
srt2web config set input.type rtmp
srt2web config save

# Módulos
srt2web modules list
srt2web modules toggle transcriber
srt2web modules debug whisper

# Salidas
srt2web outputs list
srt2web outputs add --name rtmp_1 --type rtmp --url "rtmp://..."
srt2web outputs remove recording_1
srt2web outputs toggle rtmp_1 --off

# Logs
srt2web logs --tail 50
srt2web logs --filter ERROR

# Otros
srt2web health                # Health check
srt2web stream                # Abrir stream en navegador
srt2web available             # Mostrar tipos disponibles
srt2web shell                 # Modo interactivo
```

## App Desktop (Electron)

Para usuarios no técnicos, existe una aplicación de escritorio:

```bash
cd desktop
npm install
npm run build:win     # Windows
npm run build:mac     # macOS
npm run build:linux   # Linux
```

La app empaqueta FFmpeg, el servidor Python y el dashboard en un instalador nativo.

## Optimizaciones de Rendimiento

1. **GPU**: Usar CUDA para Whisper y TTS reduce latencia significativamente
2. **Audio Mixing**: Optimizado con numpy (20ms vs 1.2s con FFmpeg)
3. **FFmpeg Pool**: Máximo 4 procesos simultáneos reutilizables
4. **Piper TTS**: Usa `length_scale` nativo en vez de FFmpeg atempo (0ms overhead)
5. **Segmentos HLS**: 4s duración, 6 segmentos en lista (buffer ~24s)
6. **Pipeline parallel**: `thread_parallel` permite procesamiento concurrente de chunks
7. **Logging optimizado**: Regex single-pass para filtros (evita O(n) string matching)

## Troubleshooting

### Error: "CUDA not available"

```bash
# Verificar instalación CUDA
nvidia-smi

# Verificar en Python
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# Reinstalar dependencias NVIDIA
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

### Error: "No input video chunk"

- Verifica que OBS esté transmitiendo
- Verifica que el intervalo de keyframes sea **10 segundos**
- Verifica que el puerto SRT (9000) esté libre
- Ajusta `buffer_size` a 3 en `pipeline` config

### Error: "Piper TTS blocked event loop"

- El loader usa subprocess para evitar bloqueo
- Timeout configurado en 90 segundos
- Logs `[PIPER_DEBUG]` siempre visibles en consola
- Verifica `device: auto` en config (fallback a CPU)

### Error: "Port already in use"

```bash
# Windows
netstat -ano | findstr :9999
taskkill /PID <pid> /F

# Linux/Mac
lsof -i :9999
kill -9 <pid>
```

### Error: WebRTC no funciona

- MediaMTX debe estar ejecutándose
- Verifica que el puerto 8889 (API MediaMTX) esté libre
- Revisa logs de MediaMTX para errores de publicación

### Latencia alta

- Reduce `chunk_duration_sec` a 10s (mínimo recomendado)
- Usa modelo Whisper `tiny` o `base`
- Asegúrate de que CUDA esté activo
- Reduce `max_vtt_entries` en subtitle_generator
- Usa `pipeline.mode: sequential` para menor latencia

## Docker

### Build Imagen

```bash
docker build -t srt2web:latest .
```

### Ejecutar Contenedor

```bash
docker run -p 9999:9999 \
  -p 9000:9000/udp \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/output:/app/output \
  -e CUDA_VISIBLE_DEVICES=0 \
  srt2web:latest
```

## Verificación Post-Instalación

```bash
# Verificar estado de módulos
curl http://localhost:9999/api/status

# Verificar configuración
curl http://localhost:9999/api/config

# Verificar health
curl http://localhost:9999/api/health

# Verificar acceso al dashboard
curl http://localhost:9999/
```

## Estructura de Logs

```
logs/
├── srt2web.log      # Log principal (rotación 10MB, 3 backups)
├── srt2web.log.1    # Backup 1
├── srt2web.log.2    # Backup 2
└── srt2web.log.3    # Backup 3
```

Formato: `[TIMESTAMP] [LEVEL] [MODULE] message`

## Monitoreo

### Endpoints de Estado

- `GET /api/status` - Estado del pipeline + métricas sistema
- `GET /api/config` - Configuración actual
- `GET /api/health` - Health check básico
- `GET /api/metrics` - Métricas GPU/CPU/RAM
- `GET /api/modules` - Estado de cada módulo
- `GET /api/outputs` - Estado de salidas múltiples

### WebSocket

```javascript
const ws = new WebSocket("ws://localhost:9999/ws/logs?token=TU_TOKEN");
ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(log.timestamp, log.level, log.message);
};
```

## Frontend Build

Si modificas el frontend:

```bash
cd frontend
npm run build:local    # Build local
cp -r dist/* ../server/static/  # Copiar a servidor
```

## Tests

```bash
# Suite completa
python -m pytest tests/unit/ -v

# Archivo específico
python -m pytest tests/unit/test_audio_mixer.py -v

# Con coverage
python -m pytest tests/ --cov=core --cov=modules --cov=server

# Frontend tests
cd frontend && npm test
```

**Estado actual**: 740 tests pasando, 0 fallando.

## Checklist de Despliegue

- [ ] Python 3.12+ instalado
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas (`pip install -r config/requirements.txt`)
- [ ] FFmpeg instalado y en PATH
- [ ] CUDA configurado (si GPU disponible)
- [ ] Modelos Whisper descargados
- [ ] Config.yaml personalizado
- [ ] Puerto 9999 disponible
- [ ] OBS configurado con SRT (keyframe 10s)
- [ ] Servidor iniciado (`start.bat`)
- [ ] Dashboard accesible en `http://localhost:9999`
- [ ] Logs verificables en `logs/srt2web.log`
- [ ] Tests pasando (`python -m pytest tests/unit/`)
