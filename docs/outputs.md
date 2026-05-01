# Sistema de Salidas Múltiples

SRT2Web soporta **múltiples salidas simultáneas**. Puedes enviar el mismo stream a HLS, RTMP, SRT, WebRTC, grabación local y archivos al mismo tiempo.

## Arquitectura

```
                    ┌──────────────┐
                    │ Video Muxer  │
                    │   (HLS/      │
                    │   WebRTC)    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Composite   │
                    │   Output     │
                    └──┬──┬──┬──┬─┘
              ┌────────┘  │  │  └────────┐
              ▼           ▼  ▼           ▼
        ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
        │ HLSOutput│ │RTMPOut │ │SRTOut  │ │WebRTCOut │
        └──────────┘ └────────┘ └────────┘ └──────────┘
              │           │
              ▼           ▼
        ┌──────────┐ ┌──────────┐
        │Recording │ │ FileOut  │
        └──────────┘ └──────────┘
```

El `CompositeOutput` gestiona todas las salidas activas. Cada output se puede habilitar/deshabilitar de forma independiente sin detener el pipeline.

## Tipos de Salida

### 1. HLS (Web/WebPlayer)

**Alias**: `web`, `webplayer`, `hls`

Streaming HTTP Live Streaming para reproducción en navegador.

```yaml
output:
  type: web
  web:
    segment_duration: 4 # Duración de cada segmento .ts (segundos)
    list_size: 6 # Número de segmentos en el playlist
    audio_offset_ms: 0 # Offset de audio (ms) para sincronización
    encoder_mode: auto # auto | cpu | gpu
```

**Output**: `output/hls/stream.m3u8` + segmentos `.ts`

**Player**: `http://localhost:9999/player`

### 2. RTMP

**Alias**: `rtmp`

Envía el stream a un servidor RTMP externo (YouTube, Twitch, etc.).

```yaml
output:
  type: rtmp
  rtmp:
    url: "rtmp://a.rtmp.youtube.com/live2/xxx"
    video_bitrate: "2500k"
    audio_bitrate: "128k"
    video_codec: h264 # h264
    preset: medium # ultrafast, fast, medium, slow
    encoder_mode: auto # auto | cpu | gpu
    audio_codec: aac
```

### 3. SRT Output

**Alias**: `srt`

Envía el stream via protocolo SRT a otro destino.

```yaml
output:
  type: srt
  srt:
    url: "srt://remote-server:9001"
    mode: caller # caller | listener
    latency_ms: 200
    stream_id: ""
    passphrase: "" # Encriptación SRT
    video_bitrate: "2500k"
    audio_bitrate: "128k"
    video_codec: h264
    preset: medium
    audio_codec: aac
```

### 4. WebRTC

**Alias**: `webrtc`

Streaming ultra baja latencia (~200ms) via WebRTC. Requiere **MediaMTX**.

```yaml
output:
  type: webrtc
  webrtc:
    path: "stream" # Path en MediaMTX
    video_codec: h264 # h264 | vp8 | av1
    audio_codec: opus
    video_bitrate: "2500k"
    video_fps: 30
    video_width: 1280
    video_height: 720
    audio_sample_rate: 48000
```

**Requisito**: MediaMTX ejecutándose (descargar desde [github.com/bluenviron/mediamtx](https://github.com/bluenviron/mediamtx))

**Player**: `http://localhost:9999/webrtc-player`

### 5. Grabación (Recording)

**Alias**: `recording`

Graba el stream continuo a un archivo local. Soporta split por tiempo o tamaño y subtítulos.

```yaml
output:
  type: recording
  recording:
    output_path: "./output/recording.mp4"
    format: mp4 # mp4 | mkv
    codec: copy # copy | h264_nvenc | libx264 | hevc_nvenc | libx265
    quality_mode: cbr # cbr | crf
    video_bitrate: "5000k" # Para CBR
    video_crf: 23 # Para CRF (18-28, menor = mejor calidad)
    audio_codec: aac # copy | aac | mp3
    audio_bitrate: "128k"
    split_mode: none # none | time | size
    split_value: 600 # Segundos (time) o MB (size)
    subtitles: burnt # none | burnt | track | vtt
    video_preset: fast # ultrafast a veryslow (reencode)
```

**Modos de subtítulos**:

| Modo    | Descripción                                  | Rendimiento       |
| ------- | -------------------------------------------- | ----------------- |
| `none`  | Sin subtítulos                               | Más rápido        |
| `burnt` | Subtítulos "quemados" en el video            | Requiere reencode |
| `track` | Pista de subtítulos separada (seleccionable) | `copy` funciona   |
| `vtt`   | Archivo VTT sidecar                          | Sin impacto       |

**Recomendado**: `codec: copy` + `subtitles: track` para grabación sin reencode con subtítulos seleccionables.

### 6. File Output

**Alias**: `file`

Guarda los chunks individuales como archivos en disco.

```yaml
output:
  type: file
  file:
    path: "./output/chunks"
    save_video: true
    save_audio: true
    save_subtitles: true
```

## Salidas Múltiples Simultáneas

Para activar varias salidas al mismo tiempo, usa la sección `outputs:` en `config.yaml`:

```yaml
# Salida principal (obligatoria)
output:
  type: web
  web:
    segment_duration: 4
    list_size: 6

# Salidas adicionales (opcionales)
outputs:
  - name: web_1
    type: web
    enabled: true
    config:
      segment_duration: 4
      list_size: 6
      encoder_mode: auto

  - name: recording_1
    type: recording
    enabled: true
    config:
      output_path: "./output/grabacion.mp4"
      codec: copy
      subtitles: track

  - name: rtmp_1
    type: rtmp
    enabled: false
    config:
      url: "rtmp://a.rtmp.youtube.com/live2/xxx"
      video_bitrate: "4000k"

  - name: webrtc_1
    type: webrtc
    enabled: false
    config:
      path: "stream"
      video_codec: h264
      audio_codec: opus
```

Cada salida puede ser:

- **Habilitada/deshabilitada** individualmente sin detener el pipeline
- **Añadida/eliminada** en tiempo real via API o dashboard
- **Configurada** con parámetros independientes

## Gestión desde el Dashboard

El dashboard incluye un panel de gestión de salidas:

1. **OutputCard** en ProcessGrid: Muestra resumen de salidas activas
2. **OutputManagerCard**: Panel completo con:
   - Lista de salidas configuradas
   - Toggle on/off por salida
   - Estadísticas por salida (chunks procesados, bytes)
   - Formulario inline para añadir nuevas salidas
   - Botón eliminar por salida

## Gestión desde CLI

```bash
# Listar salidas
srt2web outputs list

# Añadir salida
srt2web outputs add --name rtmp_youtube --type rtmp \
  --url "rtmp://a.rtmp.youtube.com/live2/xxx" \
  --config '{"video_bitrate": "4000k"}'

# Eliminar salida
srt2web outputs remove rtmp_youtube

# Toggle salida
srt2web outputs toggle rtmp_youtube --on
srt2web outputs toggle rtmp_youtube --off

# Ver estado
srt2web outputs status
```

## API REST

```bash
# Listar salidas
GET /api/outputs

# Añadir salida
POST /api/outputs
{
  "name": "rtmp_1",
  "type": "rtmp",
  "enabled": true,
  "config": {
    "url": "rtmp://...",
    "video_bitrate": "2500k"
  }
}

# Eliminar salida
DELETE /api/outputs/{name}

# Toggle salida
PUT /api/outputs/{name}/toggle
{ "enabled": true }

# Actualizar config
PUT /api/outputs/{name}/config
{ "video_bitrate": "4000k" }
```

## Factory y Registro

Los outputs se registran en `core/io_factory.py`:

```python
OutputFactory.register("webplayer", HLSOutput)
OutputFactory.register("web", HLSOutput)
OutputFactory.register("hls", HLSOutput)
OutputFactory.register("rtmp", RTMPOutput)
OutputFactory.register("recording", RecordingOutput)
OutputFactory.register("file", FileOutput)
OutputFactory.register("srt", SRTOutput)
OutputFactory.register("webrtc", WebRTCOutput)
```

Para añadir un nuevo tipo de output:

1. Crear clase en `modules/outputs/nuevo_output.py`
2. Heredar de `OutputSink` y `BaseModule`
3. Registrar en `modules/outputs/__init__.py`
4. Añadir a `VALID_OUTPUT_TYPES` en `core/config_schema.py`
5. Añadir UI en `frontend/src/components/OutputConfigForm.astro`

## Rendimiento

Cada salida adicional consume recursos adicionales:

| Output    | CPU                                 | GPU                    | Red     |
| --------- | ----------------------------------- | ---------------------- | ------- |
| HLS       | Bajo (segmentación)                 | Bajo (si encoder GPU)  | Medio   |
| RTMP      | Medio (reencode)                    | Medio (si encoder GPU) | Alto    |
| SRT       | Medio                               | Medio                  | Alto    |
| WebRTC    | Medio                               | Medio (si encoder GPU) | Alto    |
| Recording | Bajo (si copy) / Alto (si reencode) | Bajo/Medio             | Ninguno |
| File      | Bajo                                | Ninguno                | Ninguno |

**Recomendación**: Usa `codec: copy` para grabación si no necesitas reencode. Limita a 3-4 salidas simultáneas en hardware modesto.
