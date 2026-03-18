# Cambios Realizados para Mejora de Calidad de Video

## Resumen de Cambios

### 1. Mejora de la Codificación de Video
El sistema ahora usa por defecto un preset de mejor calidad en lugar del preset de máxima velocidad (`ultrafast`).

**Antes (baja calidad):**
- Preset: `ultrafast` (CRF 28)
- Calidad: Muy baja, máxima velocidad

**Después (alta calidad):**
- Preset: `slow` (CRF 16-18)
- Calidad: Alta, equilibrio calidad/velocidad

### 2. Controles de Encoder en la UI
Se añadieron controles en la página del dashboard para configurar:

**Sección "HLS Muxer" en Configuración Avanzada:**
- **Modo de Codificación**: Automático (detecta GPU), CPU, NVIDIA NVENC, AMD AMF, Intel QSV
- **Preset de Calidad**: Desde "Ultrafast" (máxima velocidad) hasta "Veryslow" (máxima calidad)
- **Calidad (CRF/CQ)**: Slider 0-51 (CPU) o 0-51 (GPU)
- **Perfil de Video**: Baseline, Main, High
- **Tuning**: Streaming (zerolatency), Cine, Animación
- **Preset GPU**: p1-p7 (p1 = máxima velocidad, p7 = máxima calidad)
- **Codec de Audio**: AAC, Opus
- **Bitrate de Audio**: 64k-512k
- **Frecuencia de Muestreo**: 44.1kHz, 48kHz

### 3. Archivos Modificados

#### `core/encoder_config.py` (NUEVO)
Clase centralizada para configuración de encoder que maneja:
- Parámetros de codificación CPU (libx264)
- Parámetros de codificación GPU (NVENC, AMF, QSV)
- Configuración de audio

#### `modules/outputs/hls_output.py`
- Integrada `EncoderConfig` para usar la nueva configuración
- Soporte para parámetros de encoder configurables
- Mejora de calidad de codificación

#### `modules/video_muxer.py`
- Integrada `EncoderConfig` para consistencia con `hls_output.py`
- Mismo sistema de configuración

#### `config.yaml`
- Añadidos parámetros de encoder configurables
- Valores recomendados por defecto:
  - `video_preset: medium` (equilibrio)
  - `video_crf: 18` (calidad buena)
  - `encoder_mode: auto` (detecta GPU automáticamente)

#### `web/index.html`
- Controles de configuración de encoder en la UI
- Selector de calidad con valores reales (CRF)
- Controles de audio

### 4. Validación de API
- Añadida validación de parámetros de encoder en `api_routes.py`
- Valores permitidos para presets de video y GPU

## Uso del Sistema

### Con OBS Studio
1. En OBS, configurar salida SRT: `srt://TU_IP:9000?mode=caller&latency=1000000`
2. Conectar al servidor SRT2Web
3. El sistema mostrará "Pipeline is running. Waiting for data..."
4. Una vez conectado OBS, se generarán segmentos HLS automáticamente

### Acceso a Configuración de Calidad
1. Acceder al dashboard: `http://localhost:9999`
2. Hacer clic en "⚙️ CONFIGURACIÓN AVANZADA"
3. Buscar sección "📦 HLS Muxer"
4. Ajustar los parámetros de encoder según necesidades

### Recomendaciones de Configuración

#### Calidad Máxima (Latencia Mayor)
- **Video Preset**: Veryslow (CRF 12)
- **Perfil**: High
- **Encoder Mode**: Auto (usará GPU si está disponible)
- **GPU Preset**: p7
- **Bitrate Audio**: 320k

#### Equilibrio Calidad/Latencia (Recomendado)
- **Video Preset**: Medium (CRF 18) o Slow (CRF 16)
- **Perfil**: High
- **Encoder Mode**: Auto
- **GPU Preset**: p3-p5
- **Bitrate Audio**: 192k

#### Baja Latencia (Streaming en Vivo)
- **Video Preset**: Fast (CRF 20)
- **Tuning**: zerolatency
- **Encoder Mode**: Auto
- **GPU Preset**: p1-p2
- **Bitrate Audio**: 128k

## Solución de Problemas

### El servidor no genera segmentos HLS
- Verificar que OBS esté conectado correctamente
- Verificar logs del servidor para errores de FFmpeg
- Asegurar que el puerto 9000 esté abierto en el firewall

### Calidad de video sigue siendo baja
- Ajustar preset a "Slow" o "Veryslow" en la UI
- Verificar que el encoder mode esté usando GPU si está disponible
- Aumentar bitrate de audio si es necesario

### El servidor no detecta GPU
- Verificar drivers de GPU actualizados
- Forzar modo CPU: `encoder_mode: cpu` en config.yaml
- Asegurar FFmpeg tiene soporte para tu GPU

## Verificación de Funcionamiento

### Estado del Pipeline
```bash
curl http://localhost:9999/api/status
```

### Configuración Actual
```bash
curl http://localhost:9999/api/config
```

### Logs del Servidor
Los logs muestran:
- `Using CPU encoder: libx264 (preset: slow, crf: 16)` - Codificación por CPU
- `Using GPU encoder: h264_nvenc (preset: p5)` - Codificación por GPU NVENC
- `HLS output reconfigured: segment=15s, encoder_mode=auto, video_preset=slow` - Reconfiguración

## Notas Importantes

- Los cambios de configuración se aplican inmediatamente (hot reload)
- La calidad de video depende de la configuración del encoder en la UI
- El sistema usa aceleración por hardware cuando está disponible
- El modo "auto" detecta automáticamente la mejor GPU disponible
- Los subtítulos y traducción continúan funcionando normalmente

## Solución de Bug de Generación de Playlists HLS

### Problema Detectado
Los archivos `master.m3u8` y `stream.m3u8` no se generaban correctamente, causando que la página index mostrara "esperando stream" indefinidamente.

### Causa Raíz
El módulo `core/encoder_config.py` incluía argumentos inválidos para el codificador NVENC:
- `-zerolatency 1` (incorrecto para NVENC, es una opción de libx264)
- `-delay 0` (causaba error "Invalid argument")

### Solución Aplicada
Se modificó `core/encoder_config.py` en el método `get_gpu_nvenc_args()`:
- Eliminados los argumentos inválidos `-delay` y `-zerolatency`
- Se mantuvieron los argumentos correctos: `-preset`, `-rc`, `-cq`, `-profile:v`

### Archivos Modificados
- `core/encoder_config.py`: Líneas 100-113 (método `get_gpu_nvenc_args`)

### Verificación
Después de aplicar el fix y reiniciar el servidor:
1. ✅ `master.m3u8` se genera correctamente
2. ✅ `stream.m3u8` se actualiza con los segmentos HLS
3. ✅ Se generan múltiples segmentos `seg_XXXXXX.ts`
4. ✅ El reproductor web puede cargar el stream
5. ✅ El pipeline procesa chunks correctamente

### Comandos de Verificación
```bash
# Verificar estado del pipeline
curl http://localhost:9999/api/status

# Verificar generación de segmentos
dir output/hls

# Verificar contenido de playlists
powershell Get-Content output/hls/master.m3u8
powershell Get-Content output/hls/stream.m3u8
```

### Notas Adicionales
- El fix requiere reiniciar el servidor para recargar el módulo `encoder_config.py`
- Los cambios se aplican automáticamente en futuros arranques
- La calidad de video mejora significativamente con codificación GPU (NVENC)
