# Documentación API - SRT2Web

## Endpoints REST

### Health Check

```http
GET /health
```

Verifica que el servidor está funcionando.

**Respuesta:**
```json
{
  "status": "ok"
}
```

---

### Estado del Pipeline

```http
GET /api/status
```

Obtiene el estado completo del pipeline incluyendo módulos.

**Respuesta:**
```json
{
  "state": "idle|running|error",
  "modules": [
    {
      "name": "string",
      "enabled": boolean,
      "state": "string"
    }
  ],
  "srt_receiving": boolean,
  "srt_url": "string"
}
```

---

### Iniciar Pipeline

```http
POST /api/start
```

Inicia el pipeline de procesamiento.

**Respuesta (200):**
```json
{
  "status": "started",
  "srt_url": "srt://127.0.0.1:9000?mode=caller&latency=400000"
}
```

**Errores:**
- `400`: Pipeline ya está corriendo

---

### Detener Pipeline

```http
POST /api/stop
```

Detiene el pipeline de procesamiento.

**Respuesta:**
```json
{
  "status": "stopped"
}
```

---

### Obtener Configuración

```http
GET /api/config
```

Obtiene la configuración actual.

**Respuesta:**
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8080
  },
  "srt": {
    "listen_port": 9000,
    "mode": "listener"
  },
  "modules": { ... }
}
```

---

### Actualizar Configuración

```http
PUT /api/config
```

Actualiza la configuración (parcial).

**Cuerpo:**
```json
{
  "config": {
    "server": {
      "port": 9000
    },
    "modules": {
      "transcriber": {
        "model": "small"
      }
    }
  }
}
```

**Validaciones:**
- `port`: 1-65535
- `latency`: >= 0
- `transcriber.model`: tiny, small, medium, large-v2, large-v3, large
- `transcriber.language`: auto, en, es, fr, de, it, pt, ja, zh, ko, ru
- `transcriber.device`: auto, cuda, cpu
- `srt.mode`: listener, caller
- `volume`: 0.0-2.0
- `speed`: 0.5-2.0

**Respuesta:**
```json
{
  "status": "updated",
  "config": { ... }
}
```

---

### Listar Módulos

```http
GET /api/modules
```

Lista todos los módulos registrados y su estado.

**Respuesta:**
```json
{
  "modules": [
    {
      "name": "string",
      "enabled": boolean,
      "state": "string",
      "status": "string"
    }
  ]
}
```

---

### Toggle Módulo

```http
PUT /api/modules/{module_name}/toggle
```

Habilita o deshabilita un módulo específico.

**Parámetros:**
- `module_name`: Nombre del módulo (transcriber, translator, etc.)

**Cuerpo:**
```json
{
  "enabled": true|false
}
```

**Módulos válidos:**
- audio_extractor
- transcriber
- translator
- subtitle_generator
- tts_engine
- audio_mixer
- video_muxer

**Respuesta:**
```json
{
  "module": "transcriber",
  "enabled": false,
  "status": { ... }
}
```

---

### Info SRT

```http
GET /api/srt-info
```

Obtiene información de conexión SRT para OBS/VMix.

**Respuesta:**
```json
{
  "mode": "listener",
  "port": 9000,
  "latency_ms": 400,
  "obs_url": "srt://YOUR_IP:9000?mode=caller&latency=400000",
  "vmix_url": "srt://YOUR_IP:9000",
  "instructions": {
    "obs": "OBS → Settings → Stream → Service: Custom → Server: srt://YOUR_IP:9000?mode=caller&latency=400000",
    "vmix": "vMix → Add Input → Stream/SRT → Hostname: YOUR_IP, Port: 9000"
  }
}
```

---

## WebSockets

### Logs en Tiempo Real

```http
WS /ws/logs
```

Recibe logs del sistema en tiempo real.

**Mensajes recibidos:**
```json
{
  "level": "info|warning|error",
  "message": "Log message"
}
```

---

## Códigos de Estado

| Código | Descripción |
|--------|-------------|
| 200 | Éxito |
| 400 | Error de validación o solicitud incorrecta |
| 404 | Recurso no encontrado |
| 422 | Error de validación de entrada |
| 500 | Error interno del servidor |

---

## Ejemplo de Uso

### Python

```python
import requests

# Iniciar pipeline
response = requests.post("http://localhost:8080/api/start")
print(response.json())

# Obtener estado
response = requests.get("http://localhost:8080/api/status")
print(response.json())

# Actualizar configuración
response = requests.put(
    "http://localhost:8080/api/config",
    json={"config": {"modules": {"transcriber": {"model": "small"}}}}
)
print(response.json())
```

### cURL

```bash
# Health check
curl http://localhost:8080/health

# Obtener estado
curl http://localhost:8080/api/status

# Iniciar pipeline
curl -X POST http://localhost:8080/api/start

# Detener pipeline
curl -X POST http://localhost:8080/api/stop
```
