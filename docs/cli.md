# Herramienta CLI

SRT2Web incluye una **herramienta de línea de comandos** completa para controlar el servidor, configurar módulos, gestionar salidas y monitorizar el pipeline sin necesidad de usar el dashboard web.

## Instalación

### Windows

```bash
# Usar el batch launcher
cli\srt2web.bat status

# O directamente con Python
python cli/srt2web.py status
```

### Linux/Mac

```bash
python cli/srt2web.py status
```

## Comandos

### Pipeline Control

```bash
# Iniciar pipeline
srt2web start

# Detener pipeline
srt2web stop

# Reiniciar pipeline
srt2web restart
```

### Estado y Monitorización

```bash
# Estado actual (una vez)
srt2web status

# Modo observación continua (actualiza cada 2s)
srt2web status --watch

# Health check
srt2web health

# Mostrar métricas del sistema
srt2web metrics
```

**Ejemplo output**:

```
┌─────────────────────────────────────────┐
│  SRT2Web Pipeline Status                │
├─────────────────────────────────────────┤
│  State:    running                      │
│  Mode:     thread_parallel              │
│  Chunks:   42 processed                 │
│  Uptime:   00:07:23                     │
│                                         │
│  CPU:  45%    Memory: 2.1 GB           │
│  GPU:  78%    VRAM: 3.2 / 8.0 GB       │
│                                         │
│  Modules:                               │
│  ✓ SRT Input      running   42 chunks   │
│  ✓ Whisper        running   42 chunks   │
│  ✓ Translator     running   42 chunks   │
│  ✓ TTS Engine     running   42 chunks   │
│  ✓ Video Muxer    running   42 chunks   │
└─────────────────────────────────────────┘
```

### Configuración

```bash
# Mostrar configuración completa
srt2web config get

# Mostrar valor específico
srt2web config get input.type
srt2web config get modules.transcriber.model

# Establecer valor
srt2web config set input.type rtmp
srt2web config set modules.transcriber.model small
srt2web config set pipeline.mode sequential
srt2web config set output.web.segment_duration 2

# Guardar configuración a config.yaml
srt2web config save

# Recargar configuración (hot-reload)
srt2web config reload
```

### Módulos

```bash
# Listar módulos
srt2web modules list

# Toggle módulo
srt2web modules toggle transcriber
srt2web modules toggle translator --off
srt2web modules toggle tts_engine --on

# Debug de módulo (información detallada)
srt2web modules debug whisper
srt2web modules debug tts_engine
srt2web modules debug video_muxer
```

**Ejemplo debug output**:

```
Module: transcriber
  Enabled:  true
  State:    running
  Device:   cuda
  Model:    tiny
  Language: en
  GPU:      NVIDIA GeForce RTX 3060
  Chunks:   42
  Latency:  ~120ms per chunk
```

### Salidas (Outputs)

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

# Ver estado de salidas
srt2web outputs status
```

### Logs

```bash
# Últimos 50 logs
srt2web logs --tail 50

# Filtrar por nivel
srt2web logs --filter ERROR
srt2web logs --filter WARNING
srt2web logs --filter INFO

# Seguir logs en tiempo real
srt2web logs --follow
```

### Otros

```bash
# Abrir stream en navegador
srt2web stream

# Mostrar tipos de input/output disponibles
srt2web available

# Modo interactivo (shell REPL)
srt2web shell

# Versión
srt2web --version
```

## Modo Interactivo (Shell)

El modo shell proporciona un REPL interactivo para control completo:

```bash
srt2web shell
```

```
SRT2Web Shell v0.6.8
Type 'help' for commands, 'exit' to quit.

srt2web> status
Pipeline: running | Chunks: 42 | Uptime: 00:07:23

srt2web> config get input.type
srt

srt2web> config set input.type rtmp
✓ Input type set to: rtmp

srt2web> modules list
  transcriber   enabled   running
  translator    enabled   running
  tts_engine    enabled   running
  video_muxer   enabled   running

srt2web> outputs list
  web_1       web       enabled   running
  recording_1 recording enabled   running

srt2web> logs --tail 5 --filter WARNING
  [WARN] Duration drift: 0.05s
  [WARN] Audio padding applied

srt2web> exit
```

## Integración con Scripts

La CLI puede usarse en scripts bash/powershell:

```bash
#!/bin/bash
# Auto-start pipeline con config específica

srt2web config set pipeline.mode sequential
srt2web config set modules.transcriber.model tiny
srt2web config save
srt2web start

# Esperar a que esté corriendo
srt2web status --watch
```

```powershell
# PowerShell: Toggle outputs basado en hora
$hour = (Get-Date).Hour
if ($hour -ge 9 -and $hour -le 18) {
    srt2web outputs toggle rtmp_youtube --on
} else {
    srt2web outputs toggle rtmp_youtube --off
}
```

## Argumentos de Línea de Comandos

```
Usage: srt2web.py [command] [subcommand] [options]

Commands:
  status      Show pipeline status
  health      Health check
  start       Start pipeline
  stop        Stop pipeline
  restart     Restart pipeline
  config      Configuration management
  modules     Module management
  outputs     Output management
  logs        Show logs
  stream      Open stream in browser
  available   Show available input/output types
  shell       Interactive shell mode
  version     Show version

Options:
  --host HOST        Server host (default: 127.0.0.1)
  --port PORT        Server port (default: 9999)
  --token TOKEN      Auth token
  --watch            Watch mode (for status)
  --tail N           Number of log lines (for logs)
  --filter LEVEL     Filter logs by level
  --follow           Follow logs in real-time
  --format FORMAT    Output format: text, json
```

## Formato JSON

Para integración con otras herramientas:

```bash
srt2web status --format json
srt2web config get --format json
srt2web modules list --format json
srt2web outputs list --format json
```

**Ejemplo JSON**:

```json
{
  "state": "running",
  "mode": "thread_parallel",
  "processed_chunks": 42,
  "uptime": "00:07:23",
  "system": {
    "cpu_percent": 45.2,
    "memory_mb": 2150.4,
    "memory_percent": 67.8,
    "gpu_usage": 78.0,
    "gpu_memory_mb": 3276
  },
  "modules": {
    "srt_input": {
      "enabled": true,
      "state": "running",
      "processed_chunks": 42
    },
    "transcriber": {
      "enabled": true,
      "state": "running",
      "processed_chunks": 42
    },
    "translator": {
      "enabled": true,
      "state": "running",
      "processed_chunks": 42
    }
  }
}
```
