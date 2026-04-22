# SRT2Web CLI

Control SRT2Web server from command line without a browser.

## Requisitos

```bash
pip install requests colorama pyyaml
```

O instala todas las dependencias:
```bash
pip install -r config/requirements.txt
```

## Uso

### Launcher Windows

```batch
cli\srt2web.bat status
cli\srt2web.bat start
cli\srt2web.bat stop
cli\srt2web.bat status --watch
```

### Python directo

```bash
python cli/srt2web.py status
python cli/srt2web.py start
python cli/srt2web.py --help
```

## Comandos

### Pipeline

```bash
srt2web status              # Ver estado del pipeline
srt2web status --watch      # Modo watch interactivo (actualiza cada 2s)
srt2web start               # Iniciar pipeline
srt2web stop                # Detener pipeline
srt2web restart             # Reiniciar pipeline
srt2web health              # Health check
srt2web available          # Tipos de input/output disponibles
```

### Configuración

```bash
srt2web config get                          # Ver config completa
srt2web config get pipeline.chunk_duration_sec  # Ver valor específico
srt2web config set pipeline.chunk_duration_sec=10  # Modificar valores
srt2web config save                        # Guardar a config.yaml
```

### Módulos

```bash
srt2web modules list              # Listar todos los módulos
srt2web modules debug transcriber  # Info de debug de un módulo
```

### Outputs

```bash
srt2web outputs list              # Listar outputs
srt2web outputs add recording --name myrecording --config output_path=./output/recording.mp4,codec=copy
srt2web outputs remove webplayer_1
srt2web outputs toggle webplayer_1
```

### Logs

```bash
srt2web logs --tail 50          # Últimos 50 logs
srt2web logs --filter error     # Filtrar por nivel
```

### Stream

```bash
srt2web stream                  # Abrir reproductor en navegador
```

### Shell interactivo

```bash
srt2web shell
# then type commands:
# status, health, start, stop, modules, outputs, logs, config, exit
```

## Autenticación

Si tienes `auth_token` configurado en `config.yaml`, la CLI lo lee automáticamente del archivo.

## API endpoints usados

| Método | Path | Descripción |
|-------|------|-------------|
| GET | `/api/status` | Estado del pipeline |
| GET | `/api/health` | Health check |
| POST | `/api/start` | Iniciar |
| POST | `/api/stop` | Detener |
| POST | `/api/restart` | Reiniciar |
| GET | `/api/config` | Ver config |
| PUT | `/api/config` | Modificar config |
| GET | `/api/modules` | Listar módulos |
| PUT | `/api/modules/{name}/toggle` | Toggle módulo |
| GET | `/api/outputs` | Listar outputs |
| POST | `/api/outputs` | Añadir output |
| DELETE | `/api/outputs/{name}` | Eliminar output |
| POST | `/api/outputs/{name}/toggle` | Toggle output |
| GET | `/api/logs` | Logs |
| GET | `/api/available` | Tipos disponibles |

## Ejemplos completos

### Iniciar stream con config

```bash
# Ver config actual
srt2web config get

# Cambiar modelo de Whisper
srt2web config set modules.transcriber.model=base

# Iniciar pipeline
srt2web start

# Ver estado en tiempo real
srt2web status --watch

# Detener
srt2web stop

# Guardar cambios
srt2web config save
```

### Gestionar outputs

```bash
# Ver outputs actuales
srt2web outputs list

# Añadir grabación a archivo
srt2web outputs add recording --name myrecording --config output_path=./output/recording.mp4,codec=h264_nvenc

# Toggle un output
srt2web outputs toggle myrecording

# Eliminar
srt2web outputs remove myrecording
```

### Modo monitor

```bash
# Watch en tiempo real
srt2web status --watch

# Logs de error
srt2web logs --filter error --tail 100
```