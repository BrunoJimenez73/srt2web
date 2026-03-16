# AGENTS.md - Guía para Agentes IA

Este documento proporciona instrucciones para agentes IA que trabajan en el proyecto SRT2Web.

## Proyecto

SRT2Web es un procesador modular de streams SRT que permite transcripción, traducción, subtitulado y doblaje (TTS) automático de video en tiempo real, distribuidos vía HLS.

## Comandos de Desarrollo

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
python main.py

# Ejecutar tests
python -m pytest tests/ -v

# Tests con coverage
python -m pytest tests/ --cov=. --cov-report=html

# Ejecutar lint
ruff check .
```

## Estructura del Proyecto

```
srt2web/
├── core/               # Núcleo del sistema
│   ├── pipeline.py     # Orquestador del pipeline
│   ├── module_base.py  # Clase base BaseModule y PipelineData
│   └── ffmpeg_utils.py # Utilidades FFmpeg y detección GPU
├── modules/            # Módulos de procesamiento
│   ├── srt_ingest.py   # Entrada SRT
│   ├── video_muxer.py  # Salida HLS
│   └── ...
├── server/             # Servidor FastAPI
│   ├── api_routes.py   # API REST
│   └── ws_routes.py   # WebSockets
├── web/               # Frontend
├── tests/             # Tests
│   ├── unit/          # Tests unitarios
│   ├── integration/   # Tests de integración
│   └── e2e/          # Tests end-to-end
├── main.py            # Punto de entrada
├── config.yaml        # Configuración
└── requirements.txt  # Dependencias
```

## Configuración

La configuración se encuentra en `config.yaml`. Los parámetros principales son:

- `server.host`, `server.port`: Host y puerto del servidor web
- `srt.listen_port`, `srt.mode`: Puerto y modo SRT (listener/caller)
- `modules.transcriber.*`: Configuración de Whisper (model, language, device)
- `modules.translator.*`: Configuración del traductor
- `modules.tts_engine.*`: Configuración de TTS
- `modules.audio_mixer.*`: Volumen y velocidad

## Testing

- **Framework**: pytest
- **Fixtures**: Definidos en `tests/conftest.py`
- **Markers**: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.live`

Ejecutar tests rápidos (excluyendo slow):
```bash
python -m pytest -m "not slow" tests/
```

## Módulos del Pipeline

1. **SRTIngest**: Recibe flujo SRT y lo fragmenta
2. **AudioExtractor**: Separa audio del video
3. **Transcriber**: Transcripción con faster-whisper
4. **Translator**: Traducción con Argos Translate
5. **SubtitleGenerator**: Genera subtítulos VTT/SRT
6. **TTSEngine**: Generación de voz TTS
7. **AudioMixer**: Mezcla audio original con doblaje
8. **VideoMuxer**: Empaquetado HLS

## Notas Importantes

- El proyecto usa medición exacta de duración con ffprobe para evitar tirones en HLS
- Soporta aceleración GPU: NVIDIA (NVENC), AMD (AMF), Intel (QSV)
- La configuración puede cambiarse en caliente sin reiniciar el pipeline
- En Windows, usa taskkill para limpiar procesos FFmpeg zombies
