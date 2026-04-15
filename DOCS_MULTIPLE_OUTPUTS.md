# SRT2Web - Múltiples Salidas Simultáneas

## Introducción

SRT2Web ahora soporta múltiples salidas simultáneas, permitiendo emitir a diferentes destinos al mismo tiempo. Esto incluye:

- Múltiples conexiones SRT
- Grabación local en archivos
- Streaming RTMP a plataformas externas
- Streaming Web/HLS para navegadores

## Configuración

### 1. Configuración en config.yaml

Para habilitar múltiples salidas, modifica tu archivo `config.yaml`:

```yaml
output:
  # Habilitar modo de múltiples salidas
  outputs:
    # Salida SRT 1 - Emisión principal
    - type: srt
      name: srt_main
      url: srt://localhost:9001
      mode: caller
      latency_ms: 200
      stream_id: main_stream
      video_bitrate: "2500k"
      audio_bitrate: "128k"
      video_codec: "h264"
      preset: "medium"
      audio_codec: "aac"

    # Salida SRT 2 - Backup o streaming adicional
    - type: srt
      name: srt_backup
      url: srt://backup-server:9002
      mode: caller
      latency_ms: 300
      stream_id: backup_stream
      video_bitrate: "2000k"
      audio_bitrate: "96k"
      video_codec: "h264"
      preset: "fast"
      audio_codec: "aac"

    # Salida de Archivo - Grabación local
    - type: file
      name: local_recording
      save_video: true
      save_audio: true
      save_subtitles: true
      path: "./recordings"

    # Salida RTMP - Streaming a plataforma externa
    - type: rtmp
      name: rtmp_stream
      url: "rtmp://rtmp-server/live/stream"
      video_bitrate: "3000k"
      audio_bitrate: "128k"
      video_codec: "h264"
      preset: "fast"
      audio_codec: "aac"
      encoder_mode: "gpu_nvenc"

    # Salida Web/HLS - Streaming HTTP
    - type: web
      name: hls_stream
      segment_duration: 4
      list_size: 6
      audio_offset_ms: 0
      encoder_mode: "auto"
```

### 2. Interfaz Web

La interfaz web ha sido actualizada con un nuevo panel de gestión de salidas:

1. **Panel de Gestión de Salidas**: Accesible desde el dashboard principal
2. **Formulario de Configuración**: Permite añadir nuevas salidas con diferentes tipos
3. **Tarjetas de Estado**: Muestra el estado en tiempo real de cada salida
4. **Controles**: Habilitar/deshabilitar, reconectar y eliminar salidas

## Tipos de Salida Soportados

### SRT (Secure Reliable Transport)

- **URL**: `srt://host:port`
- **Modo**: `caller` (cliente) o `listener` (servidor)
- **Latencia**: Configurable en milisegundos
- **Stream ID**: Identificador opcional
- **Contraseña**: Seguridad opcional

### Archivo (File)

- **Guardar Video**: Opción para grabar video
- **Guardar Audio**: Opción para grabar audio
- **Guardar Subtítulos**: Opción para grabar subtítulos
- **Directorio**: Ruta donde se guardarán los archivos

### RTMP (Real-Time Messaging Protocol)

- **URL**: `rtmp://host/app/stream`
- **Video Bitrate**: Velocidad de bits de video
- **Audio Bitrate**: Velocidad de bits de audio
- **Video Codec**: Codec de video (ej: h264)
- **Audio Codec**: Codec de audio (ej: aac)
- **Encoder Mode**: CPU, GPU NVENC o GPU VAAPI

### Web/HLS (HTTP Live Streaming)

- **Segment Duration**: Duración de cada segmento (segundos)
- **List Size**: Número de segmentos en la lista
- **Audio Offset**: Compensación de audio (ms)
- **Encoder Mode**: CPU, GPU NVENC o GPU VAAPI

## API Endpoints

### GET /api/outputs

Obtiene todas las salidas y su estado:

```json
{
  "statuses": [
    {
      "name": "srt_main",
      "type": "srt",
      "state": "running",
      "enabled": true,
      "processed_chunks": 15,
      "last_process_time_ms": 45.2,
      "extra": {
        "connection_status": "connected"
      }
    }
  ],
  "errors": {
    "srt_backup": "Connection timeout"
  }
}
```

### POST /api/outputs

Añade una nueva salida:

```json
// Request
{
  "type": "srt",
  "name": "srt_new",
  "url": "srt://localhost:9003",
  "mode": "caller",
  "latency_ms": 200
}

// Response
{
  "name": "srt_new",
  "type": "srt",
  "state": "starting",
  "enabled": true,
  "processed_chunks": 0,
  "last_process_time_ms": 0
}
```

### DELETE /api/outputs/{name}

Elimina una salida existente.

### POST /api/outputs/{name}/reconnect

Intenta reconectar una salida que falló.

### PATCH /api/outputs/{name}/enable

Habilita o deshabilita una salida.

## Ejemplos de Uso

### 1. Streaming a múltiples plataformas

```yaml
# Emisión principal a SRT
- type: srt
  name: srt_main
  url: srt://localhost:9001
  mode: caller
  latency_ms: 200

# Backup a SRT secundario
- type: srt
  name: srt_backup
  url: srt://backup-server:9002
  mode: caller
  latency_ms: 300

# Grabación local
- type: file
  name: local_recording
  save_video: true
  save_audio: true
  save_subtitles: true
  path: "./recordings"

# Streaming a YouTube/Twitch
- type: rtmp
  name: rtmp_youtube
  url: "rtmp://a.rtmp.youtube.com/live2/stream-key"
  video_bitrate: "4500k"
  audio_bitrate: "128k"
  encoder_mode: "gpu_nvenc"
```

### 2. Producción profesional

```yaml
# Entrada principal
- type: srt
  name: srt_input
  url: srt://localhost:9000
  mode: listener
  latency_ms: 100

# Monitorización local
- type: file
  name: monitor_recording
  save_video: true
  save_audio: true
  save_subtitles: true
  path: "./monitor"

# Streaming a CDN
- type: rtmp
  name: cdn_stream
  url: "rtmp://cdn-server/live/stream"
  video_bitrate: "6000k"
  audio_bitrate: "192k"
  encoder_mode: "gpu_nvenc"

# Web streaming para espectadores
- type: web
  name: web_stream
  segment_duration: 6
  list_size: 10
  encoder_mode: "gpu_nvenc"
```

## Gestión de Errores

El sistema maneja automáticamente los errores de conexión:

1. **Detección**: Monitoriza constantemente el estado de cada salida
2. **Reconexión**: Intenta reconectar automáticamente con backoff exponencial
3. **Notificación**: Muestra errores en la interfaz web
4. **Recuperación**: Permite reconexión manual desde la interfaz

## Rendimiento

- **Concurrencia**: Soporta múltiples salidas simultáneas
- **Procesamiento**: Pipeline optimizado para throughput
- **GPU**: Aceleración hardware disponible para codificación
- **Latencia**: Configurable por salida individual

## Seguridad

- **Autenticación**: Token basado en JWT para API
- **Encriptación**: SRT soporta encriptación
- **Validación**: Configuración validada antes de iniciar
- **Auditoría**: Logs de todas las operaciones

## Troubleshooting

### Problema: Salida no se conecta

1. **Verificar URL**: Asegúrate de que la URL es correcta
2. **Verificar puertos**: Confirma que el puerto está abierto
3. **Verificar firewall**: Asegúrate que no hay bloqueos
4. **Verificar encoder**: Confirma que el encoder está disponible

### Problema: Latencia alta

1. **Ajustar latencia SRT**: Configura menor latencia si es posible
2. **Verificar red**: Comprueba la calidad de la conexión
3. **Optimizar bitrate**: Reduce bitrate si es necesario

### Problema: GPU no disponible

1. **Verificar drivers**: Asegúrate que los drivers GPU están actualizados
2. **Verificar CUDA**: Para NVIDIA, verifica que CUDA está instalado
3. **Fallback**: El sistema automáticamente usa CPU si GPU no está disponible

## Próximos Pasos

- [ ] Monitorización avanzada de cada salida
- [ ] Balanceo de carga entre múltiples salidas
- [ ] Configuración dinámica de bitrate
- [ ] Integración con sistemas de producción
- [ ] Estadísticas detalladas por salida