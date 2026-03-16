# Estructura y Arquitectura Técnica — SRT2Web

Este documento detalla el funcionamiento interno de SRT2Web para facilitar su mantenimiento o la integración de nuevas funcionalidades por parte de otros desarrolladores o IA.

## 📁 Estructura de Archivos

- `/core`: Núcleo del sistema.
  - `pipeline.py`: El orquestador que gestiona el hilo de procesamiento y el flujo de datos.
  - `module_base.py`: Clase base `BaseModule` y el objeto `PipelineData`.
  - `ffmpeg_utils.py`: Lógica de detección de GPU, medición de duración y descarga de binarios.
- `/modules`: Módulos de procesamiento independientes.
  - `srt_ingest.py`: Entrada de datos (FFmpeg SRT listener).
  - `video_muxer.py`: Salida de datos (HLS packaging con acel. hardware).
- `/server`: Servidor web FastAPI.
  - `api_routes.py`: Gestión de control (Start/Stop/Config).
  - `ws_routes.py`: Streaming de logs vía WebSockets.
- `/web`: Frontend (HTML/CSS/JS).
- `/output`: Carpeta temporal donde se procesan los chunks.
  - `/chunks`: Fragmentos de video originales recibidos.
  - `/hls`: El stream final listo para el navegador.

## 🔄 Flujo de Datos (The Pipeline)

El corazón del sistema es el objeto `PipelineData`. Cada vez que el `SRTIngest` detecta un nuevo archivo `.ts` de 4 segundos, crea una instancia de este objeto y la lanza al pipeline.

### PipelineData contiene:
- `chunk_index`: Índice correlativo para sincronización.
- `video_chunk_path`: Ruta al video original.
- `duration`: Duración exacta (medida con ffprobe) para evitar saltos.
- `transcript` / `translated_text`: Texto procesado.
- `dubbed_audio_path`: Ruta al audio AI generado.

Los módulos modifican este objeto y pasan la ruta del archivo procesado al siguiente.

## ⚡ Soluciones Técnicas Clave

### 1. Eliminación de Tirones (Seamless HLS)
Para evitar que el video se detenga cada 4 segundos, el `VideoMuxer` calcula un `offset` de tiempo acumulado. 
```python
offset_sec = f"{self._total_duration_emitted:.3f}"
```
Esto le dice al reproductor que el segmento B empieza exactamente donde terminó el A, sin micro-huecos.

### 2. Aceleración por Hardware
El sistema consulta los encoders disponibles en FFmpeg:
- `h264_nvenc` (NVIDIA) - Recomendado.
- `h264_amf` (AMD)
- `h264_qsv` (Intel)
Si no hay GPU, cae automáticamente a `libx264` (CPU).

### 3. Hot-Reloading
La clase `Pipeline` tiene el método `reconfigure()`. Cuando el usuario cambia el volumen en la web, se llama a este método que actualiza las variables internas de los módulos en tiempo real sin romper el hilo de ejecución.

### 4. Limpieza de Procesos
En Windows, FFmpeg puede quedar "zombie" bloqueando puertos. El sistema usa:
```python
subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)])
```
Esto asegura que el puerto SRT (9000) quede libre instantáneamente al pulsar Stop.

## 🛠 Guía para Continuar el Trabajo

### Próximas Implementaciones Recomendadas:
1. **Detección de Idioma Dinámica**: Cambiar el modelo de Whisper de `Spanish` fijo a `Auto` y re-cargar el traductor sobre la marcha.
2. **Multi-Idioma WebVTT**: Modificar `SubtitleGenerator` para emitir múltiples pistas `.vtt` y declararlas en el `master.m3u8`.
3. **Optimización de Memoria**: Un sistema de limpieza que elimine archivos del directorio `output` más antiguos de 10 minutos.

## 🚦 Estados de Módulo
- `IDLE`: Esperando.
- `STARTING`: Cargando modelos o inicializando archivos.
- `RUNNING`: Procesando activamente.
- `ERROR`: Fallo crítico (ver logs del sistema).

## 🧪 Arquitectura de Testing

### Framework
- **pytest** con plugins: `anyio`, `typeguard`, `mcp`
- **FastAPI TestClient** para tests de API
- **Playwright** para tests e2e (opcional)

### Principios de Testing

1. **Tests Unitarios**: Aislados, sin dependencias externas
2. **Fixtures**: Configuración reutilizable via `conftest.py`
3. **Mocking**: Minimizar dependencias de servicios externos

### Configuración (`pytest.ini`)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts = -v --tb=short --strict-markers

markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    live: marks tests that require live server
```

### Cobertura Actual
- `core/config_manager.py`: 18 tests
- `core/pipeline.py`: 15 tests
- `server/api_routes.py`: 53 tests (expandido)
