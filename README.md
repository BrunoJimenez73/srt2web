# SRT to Web Stream Server

Convierte streams SRT o RTMP a HLS para reproducción web en tiempo real.

## Requisitos

- Node.js 18+
- FFmpeg (incluido en ffmpeg-static)

## Instalación

```bash
npm install
```

## Uso

### SRT (Recibe stream de OBS)

```bash
# Usar puerto SRT por defecto (9999)
npm start

# Especificar puerto SRT
node index.js --srt-port 8080

# Con puerto HTTP custom
node index.js --srt "srt://127.0.0.1:9999?mode=listener" --port 3000
```

### RTMP (Recibe de un servidor RTMP)

```bash
# RTMP con puerto por defecto
node index.js --rtmp "rtmp://localhost:1935/live/test"

# RTMP con puerto HTTP custom
node index.js --rtmp "rtmp://192.168.1.100:1935/live/app" --port 8080
```

## Configuración OBS

### Para SRT:
1. **OBS → Configuración → Streaming**
2. **Servicio**: Custom
3. **Servidor**: `srt://127.0.0.1:9999?mode=listener`
4. **Stream Key**: (vacío)
5. **Latency**: 2000ms
6. Click en **Iniciar transmisión**

### Para RTMP:
1. **OBS → Configuración → Streaming**
2. **Servicio**: Custom
3. **Servidor**: `rtmp://localhost:1935/live/test`
4. **Stream Key**: (vacío)
5. Click en **Iniciar transmisión**

## Opciones de Línea de Comandos

| Opción | Descripción | Default |
|--------|-------------|---------|
| `-s, --srt <uri>` | URI SRT | `srt://127.0.0.1:9000?mode=listener` |
| `-r, --rtmp <uri>` | URL RTMP | - |
| `-p, --port <port>` | Puerto HTTP | 8089 |
| `--lang <code>` | Idioma de traducción | spa |
| `--no-translate` | Solo STT sin traducción | - |
| `-h, --help` | Mostrar ayuda | - |

## Output

Al iniciar, verás:
```
=== SRT/RTMP to HLS Stream Server ===
Stream URI: srt://127.0.0.1:9999?mode=listener
HTTP Port:  3000
Output Dir: C:\Users\...\AppData\Local\Temp\hls_1234567890
=======================================

Starting FFmpeg...
Waiting for HLS segments...
Segments: 3/3... 
Segments ready!

✓ Server ready!
  Stream URL: http://localhost:3000/stream.html
  HLS Playlist: http://localhost:3000/stream.m3u8

Press Ctrl+C to stop
```

## Reproducir el Stream

Abre en tu navegador: `http://localhost:3000/stream.html`

O usa un reproductor HLS como:
- VLC: `http://localhost:3000/stream.m3u8`
- Video.js compatible

## Subtítulos Automáticos

El servidor incluye transcripción y traducción en tiempo real:

- **STT**: Whisper (offline)
- **Traducción**: NLLB-200 (offline)
- **Subtítulos**: `http://localhost:<puerto>/subtitles.vtt`

### Opciones de traducción

```bash
# Traducción inglés → español (por defecto)
node index.js --srt "srt://127.0.0.1:9000?mode=listener"

# Traducir a otro idioma
node index.js --srt "srt://127.0.0.1:9000?mode=listener" --lang fra

# Solo transcripción sin traducción
node index.js --srt "srt://127.0.0.1:9000?mode=listener" --no-translate
```

### Notas
- La primera ejecución descarga modelos (~500MB)
- Procesamiento en CPU (puede ser lento)
- Requiere buen hardware para tiempo real

## Solución de Problemas

### OBS no se conecta al servidor SRT
- Verifica que el puerto SRT no esté en uso
- Asegúrate que OBS tiene la URI correcta
- Revisa que el firewall permita conexiones

### El stream no aparece
- Verifica que OBS esté transmitiendo
- Revisa los logs de FFmpeg en la terminal
- Asegúrate que el códec de video es H.264

### Tironceo en la reproducción
- Aumenta `--hls-list-size` en el código si es necesario
- Asegura buena conexión de red
- Usa `--hls-time 4` para segmentos más grandes
