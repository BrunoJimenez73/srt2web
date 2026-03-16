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

La configuración se encuentra en `config.yaml`. La estructura es jerárquica:

- `server.host`, `server.port`: Host y puerto del servidor web
- `input.srt.listen_port`, `input.srt.mode`: Puerto y modo SRT
- `modules.transcriber.*`: Configuración de Whisper (model, language, device)
- `modules.translator.*`: Configuración del traductor (source_lang, target_lang)
- `modules.tts_engine.*`: Configuración de TTS (voice, speed)
- `modules.audio_mixer.*`: volúmenes (original_volume, dubbed_volume)
- `modules.video_muxer.*`: Configuración de salida HLS

## Testing

- **Framework**: pytest
- **Unit Tests**: Cobertura exhaustiva en `tests/unit/` para todos los módulos y el core.
- **Mocking**: Se utilizan mocks para dependencias pesadas (FFmpeg, WhisperModel, ArgosTranslate, etc.) para permitir tests rápidos y sin hardware específico.
- **Fixtures**: Definidos en `tests/conftest.py`
- **Markers**: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.live`

Ejecutar todos los tests unitarios:
```bash
python -m pytest tests/unit/ -v
```

Ejecutar tests con reporte de cobertura:
```bash
python -m pytest tests/unit/ --cov=modules --cov=core --cov-report=term-missing
```

## Módulos del Pipeline

1. **SRTIngest**: Recibe flujo SRT y lo fragmenta en carpetas `.ts`
2. **AudioExtractor**: Extrae audio `.wav` de los fragmentos de video
3. **Transcriber**: Transcripción de audio a texto con faster-whisper
4. **Translator**: Traducción de texto entre idiomas (Argos Translate)
5. **SubtitleGenerator**: Genera subtítulos WebVTT (rolling) y SRT (per-chunk)
6. **TTSEngine**: Generación de audio doblado (Edge-TTS o Piper)
7. **AudioMixer**: Mezcla audio original (con ducking) y TTS
8. **VideoMuxer**: Empaqueta video y audio final en un stream HLS compatible con web

## Notas Importantes

- El proyecto usa medición exacta de duración con ffprobe para evitar tirones en HLS
- Soporta aceleración GPU: NVIDIA (NVENC), AMD (AMF), Intel (QSV), VAAPI
- La configuración puede cambiarse en caliente (hot-reload) a través de la API
- En Windows, se utiliza `taskkill /F /T` para asegurar la limpieza de procesos FFmpeg
