# Herramienta CLI

SRT2Web incluye una **herramienta de línea de comandos** completa para controlar el servidor, configurar módulos, gestionar salidas y monitorizar el pipeline.

## Instalación

La CLI se instala como parte del paquete Python:

```bash
pip install -r config/requirements.txt
# El entry point srt2web-tui queda disponible
```

### Entry Points

| Comando        | Descripción                                                  |
| -------------- | ------------------------------------------------------------ |
| `srt2web-tui`  | CLI completa + TUI interactiva (Click, vía `cli.main:cli_entry`) |
| `srt2web`      | (legacy) Entry point antiguo, no usar para nuevo desarrollo  |

## Uso General

```bash
srt2web-tui [--server URL] [--token TOKEN] [--json] <comando> [subcomando] [opciones]
```

- `--server`, `-s`: URL base del servidor (default: `http://localhost:9999`)
- `--token`, `-t`: Token de autenticación para servidores protegidos
- `--json`: Salida en formato JSON
- Sin subcomando: lanza la **TUI interactiva**

## Comandos Disponibles

### Pipeline Control

```bash
srt2web-tui pipeline start      # Iniciar pipeline
srt2web-tui pipeline stop       # Detener pipeline
srt2web-tui pipeline restart    # Reiniciar pipeline
```

### Estado y Monitorización

```bash
srt2web-tui status              # Estado del pipeline + recursos
srt2web-tui status --json       # Salida JSON estructurada
srt2web-tui health              # Health check detallado (input, output, circuit breakers)
```

**Ejemplo output `status`**:

```
Pipeline: running | Chunks: 42 | Mode: thread_parallel
Modules:
  audio_extractor: running ✓ (chunks: 42, last: 15ms)
  transcriber: running ✓ (chunks: 42, last: 120ms)
  translator: running ✓ (chunks: 42, last: 8ms)
  tts_engine: running ✓ (chunks: 42, last: 350ms)
  video_muxer: running ✓ (chunks: 42, last: 60ms)
```

**Ejemplo output `health`**:

```
Status: healthy
Pipeline: running
Uptime: 443s
Memory: 2150 MB (67.8%)
Chunks processed: 42
Input: receiving=true (srt)
Output: streaming=true (web)
Modules:
  audio_extractor: running
  transcriber: running
```

### Configuración

```bash
srt2web-tui config                      # Árbol completo de configuración
srt2web-tui config server.port          # Valor específico (dotted key)
srt2web-tui config input.type rtmp      # Establecer valor
```

Soporta claves anidadas con notación dotted (`modules.transcriber.model`, `pipeline.mode`, etc.).

### Módulos

```bash
srt2web-tui module list                 # Listar todos los módulos con estado
srt2web-tui module toggle transcriber    # Toggle (activar/desactivar)
srt2web-tui module toggle transcriber --enable
srt2web-tui module toggle translator --disable
srt2web-tui module debug transcriber    # Información detallada del módulo
```

### Salidas (Outputs)

```bash
srt2web-tui output list                 # Listar salidas activas
srt2web-tui output add rtmp --name rtmp_1 --config '{"url":"rtmp://..."}'
srt2web-tui output remove rtmp_1        # Eliminar salida
srt2web-tui output toggle rtmp_1 --enable
srt2web-tui output toggle rtmp_1 --disable
srt2web-tui output update rtmp_1 --config '{"video_bitrate":"4000k"}' --enable
```

### Presets

```bash
srt2web-tui preset list                 # Listar presets disponibles
srt2web-tui preset save mi-config       # Guardar configuración actual como preset
srt2web-tui preset apply mi-config      # Aplicar preset
srt2web-tui preset delete mi-config     # Eliminar preset
```

### Grabaciones

```bash
srt2web-tui recording list              # Listar grabaciones
srt2web-tui recording delete grabacion_01  # Eliminar grabación
```

### Input

```bash
srt2web-tui input info                  # Información del input actual
```

### Red

```bash
srt2web-tui network info                # Información de red
```

### Logs

```bash
srt2web-tui logs                        # Últimos 50 logs (default)
srt2web-tui logs --tail 100             # Número de líneas
srt2web-tui logs --level ERROR          # Filtrar por nivel
srt2web-tui logs --no-follow            # Sin seguimiento en tiempo real
srt2web-tui logs --follow --level WARNING  # Seguir logs filtrados
```

### TUI Interactiva

```bash
srt2web-tui tui                         # Lanzar TUI explícitamente
srt2web-tui                             # Lo mismo (default sin subcomando)
```

La TUI replica el dashboard web con:

- **StatusBar**: Estado del pipeline, chunks procesados, modo, reloj
- **MetricsPanel**: Barras CPU/RAM/GPU con sparklines
- **ModuleGrid**: 8 cards (Input, Whisper, Translate, TTS, Subtitle, AudioMixer, HLS, Output)
- **ConfigPanel**: Vista YAML de configuración
- **LogPanel**: Logs en vivo con coloreado por nivel

Atajos de teclado:

| Tecla    | Acción                        |
| -------- | ----------------------------- |
| `Space`  | Iniciar/detener pipeline      |
| `S`      | Guardar configuración         |
| `L`      | Toggle panel de logs          |
| `C`      | Toggle panel de configuración |
| `O`      | Toggle panel de salidas       |
| `?`      | Pantalla de ayuda             |
| `Q`      | Salir                         |

## Salida JSON

Todos los comandos soportan `--json` para integración con scripts:

```bash
srt2web-tui status --json
srt2web-tui health --json
srt2web-tui module list --json
srt2web-tui output list --json
```

**Ejemplo**:

```json
{
  "state": "running",
  "mode": "thread_parallel",
  "processed_chunks": 42,
  "uptime_seconds": 443,
  "system": {
    "cpu_percent": 45.2,
    "memory_mb": 2150.4,
    "memory_percent": 67.8
  },
  "modules": [
    {
      "name": "transcriber",
      "state": "running",
      "enabled": true,
      "processed_chunks": 42,
      "last_process_time_ms": 120
    }
  ]
}
```

## Integración con Scripts

**PowerShell**:

```powershell
# Iniciar pipeline con configuración específica
srt2web-tui config set pipeline.mode sequential
srt2web-tui config set modules.transcriber.model tiny
srt2web-tui pipeline start

# Toggle outputs basado en hora
$hour = (Get-Date).Hour
if ($hour -ge 9 -and $hour -le 18) {
    srt2web-tui output toggle rtmp_youtube --enable
} else {
    srt2web-tui output toggle rtmp_youtube --disable
}
```

**Bash**:

```bash
#!/bin/bash
# Auto-start pipeline con health check
srt2web-tui config set pipeline.mode sequential
srt2web-tui config set modules.transcriber.model tiny
srt2web-tui pipeline start

# Verificar que esté corriendo
srt2web-tui health --json | grep '"status": "healthy"'
```
