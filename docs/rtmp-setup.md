# Configuración RTMP para SRT2Web

## Visión General

SRT2Web soporta RTMP como protocolo de entrada y salida. Esto permite:
- Recibir streams RTMP desde OBS, FFmpeg u otras fuentes
- Enviar streams RTMP procesados a YouTube, Twitch u otros destinos

## Configuración de Entrada RTMP

### 1. Configurar config.yaml

```yaml
input:
  type: rtmp
  rtmp:
    url: rtmp://localhost/live/stream
    mode: pull  # Opciones: pull, push
    listen: false
    chunk_duration_sec: 6  # Debe coincidir con keyframe interval de OBS

modules:
  rtmp_input:
    enabled: true
    type: rtmp
    url: rtmp://localhost/live/stream
    mode: pull
    chunk_duration_sec: 6
```

### 2. Modos de Operación

#### Modo Pull (Recomendado)
- FFmpeg se conecta a un servidor RTMP existente (Node Media Server)
- OBS envía el stream al servidor
- SRT2Web recibe el stream del servidor

```yaml
mode: pull
listen: false
```

#### Modo Push
- FFmpeg actúa como servidor RTMP
- OBS se conecta directamente a SRT2Web

```yaml
mode: push
listen: true
```

### 3. Configurar OBS

**Output Settings**:
- Streaming Type: Custom Streaming Server
- Server: `rtmp://localhost:1935/live/stream`
- Stream Key: `stream`

**Encoder Settings**:
- Encoder: NVENC (H.264) o x264
- Rate Control: CBR
- Bitrate: 2500-5000 Kbps
- Keyframe Interval: **2 segundos** (CRÍTICO - debe coincidir con chunk_duration_sec)
- Preset: Quality o Max Quality
- Profile: High

**Audio Settings**:
- Codec: AAC
- Bitrate: 128 Kbps
- Sample Rate: 48 kHz

## Configuración de Salida RTMP

### 1. Configurar config.yaml

```yaml
output:
  type: web  # O webplayer, rtmp, file

modules:
  rtmp_output:
    enabled: true
    type: rtmp
    url: rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY
    video_bitrate: 2500k
    audio_bitrate: 128k
```

### 2. Múltiples Outputs Simultáneos

El sistema soporta múltiples outputs simultáneos. Para habilitar:

```yaml
# En config.yaml, agregar múltiples outputs modules
modules:
  webplayer_output:
    enabled: true
    type: webplayer
    # ... configuración webplayer
  
  rtmp_output:
    enabled: true
    type: rtmp
    url: rtmp://a.rtmp.youtube.com/live2/YOUR_KEY
    video_bitrate: 2500k
    audio_bitrate: 128k
```

## Arquitectura

### Flujo de Datos

```
OBS/FFmpeg → RTMP Input → Pipeline (Transcripción → Traducción → TTS → Subtítulos → AudioMixer → VideoMux) → Output (HLS/RTMP/File)
```

### Módulos de Entrada

Los inputs se registran como módulos en el pipeline:
- `InputModuleWrapper` envuelve `RTMPInput`, `SRTInput`, `FileInput`
- Solo un input activo a la vez
- Cambio dinámico requiere reiniciar pipeline

### Módulos de Salida

Los outputs se registran como módulos en el pipeline:
- `OutputModuleWrapper` envuelve `HLSOutput`, `RTMPOutput`, `FileOutput`
- Múltiples outputs pueden estar activos simultáneamente
- `OutputMultiplexer` gestiona la escritura a múltiples destinos

## Solución de Problemas

### OBS no conecta

1. Verificar que Node Media Server está corriendo:
   ```bash
   # Revisar logs del servidor SRT2Web
   ```

2. Verificar puerto 1935:
   ```bash
   netstat -an | grep 1935
   ```

3. Probar conexión manual:
   ```bash
   ffmpeg -re -i test.mp4 -c copy -f flv rtmp://localhost/live/stream
   ```

### Audio/video no sincronizados

1. Verificar keyframe interval en OBS (debe ser 2 segundos)
2. Verificar chunk_duration_sec en config.yaml (debe coincidir)
3. Revisar logs de VideoMuxer para drift

### Stream se cae frecuentemente

1. Aumentar bitrate en OBS (2500-5000 Kbps)
2. Verificar conexión de red
3. Revisar logs de reconexión

## Logs Relevantes

```
[INFO] Starting Node Media Server for RTMP input...
[INFO] Node Media Server started - OBS can connect to rtmp://localhost:1935/live/stream
[INFO] Starting RTMP input (mode=pull, listen=False, chunk=6s)
[INFO] Full RTMP command: ffmpeg -y -i rtmp://localhost/live/stream ...
```

## Configuración Avanzada

### Cambiar Puerto RTMP

Node Media Server usa puerto 1935 por defecto. Para cambiar:

```python
# En main.py, modificar la llamada a start_rtmp_server()
start_rtmp_server(port=1936)
```

### Custom RTMP Server

Para usar un servidor RTMP personalizado:

```yaml
input:
  type: rtmp
  rtmp:
    url: rtmp://mi-servidor.com/live/stream
    mode: pull
    listen: false
```

## Ejemplos de Configuración

### Solo HLS (Web Player)

```yaml
input:
  type: rtmp
  rtmp:
    mode: pull
    chunk_duration_sec: 6

output:
  type: web

modules:
  rtmp_input:
    enabled: true
```

### HLS + RTMP Output

```yaml
input:
  type: rtmp
  rtmp:
    mode: pull
    chunk_duration_sec: 6

modules:
  rtmp_input:
    enabled: true
  
  webplayer_output:
    enabled: true
    type: webplayer
  
  rtmp_output:
    enabled: true
    type: rtmp
    url: rtmp://a.rtmp.youtube.com/live2/YOUR_KEY
```

## Comandos Útiles

```bash
# Iniciar servidor
Arrancar_Servidor.bat

# Reconstruir frontend
cd frontend && npm run build:local
cp -r frontend/dist/* server/static/

# Ejecutar tests RTMP
python -m pytest tests/unit/test_rtmp_input.py -v
```

## Notas Importantes

1. **Keyframe Interval**: Debe ser exactamente 2 segundos en OBS
2. **Chunk Duration**: Debe ser múltiplo del keyframe interval (ej: 6 segundos)
3. **Puerto 1935**: Usado por Node Media Server
4. **Sincronización**: VideoMuxer maneja la sincronización audio/video
5. **GPU Encoding**: Soportado (NVENC, AMF, QSV, VideoToolbox)