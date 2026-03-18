# SRT2Web — Procesador Modular de Streams SRT

SRT2Web es una solución profesional, gratuita y de alto rendimiento para procesar flujos de video en tiempo real vía protocolo SRT. Permite realizar transcripción, traducción, subtitulado y doblaje (TTS) automático y distribuirlo a través de una página web mediante HLS.

## 🚀 Características Principales

- **Ingesta SRT Robusta**: Recibe señales de OBS, vMix u otros codificadores SRT.
- **Transcripción de Alta Precisión**: Basado en `faster-whisper` para mínima latencia.
- **Traducción Offline Gratuita**: Utiliza `Argos Translate` para privacidad total y coste cero.
- **Subtitulado WebVTT Dual**: Genera subtítulos "quemados" (SRT) o nativos de navegador (WebVTT).
- **Doblaje Inteligente (AI Dubbing)**: Generación de audio TTS con "ducking" (atenúa el audio original automáticamente).
- **Aceleración por Hardware (GPU)**: Detección automática de drivers **NVIDIA (NVENC)**, **AMD (AMF)** e **Intel (QSV)** para procesamiento fluido.
- **Panel de Control Moderno**: Interfaz web premium con logs en tiempo real y configuración "en caliente".

## 🛠 Instalación

### Requisitos Previos

1. **Python 3.10+**
2. **FFmpeg**: El sistema intentará descargarlo automáticamente, pero se recomienda tenerlo instalado en el sistema.
3. **GPU (Opcional)**: Se recomienda una GPU NVIDIA para el uso de `cuda` en la transcripción y `nvenc` en el video.

### Pasos

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
python main.py
```

## 🔌 Conectando con OBS / vMix

1. En la web de administración (por defecto `http://localhost:8080`), pulsa **Start Pipeline**.
2. En OBS → Ajustes → Emisión → Servicio: Personalizado.
3. Servidor: `srt://TU_IP:9000?mode=caller&latency=400000` (400ms de latencia).
4. El sistema empezará a procesar y verás los fragmentos en el log.

## 🏗 Arquitectura del Sistema

El proyecto sigue un diseño **Modular Basado en Pipeline**:

1. **SRTIngest**: Recibe el flujo y lo fragmenta en trozos de 4 segundos.
2. **AudioExtractor**: Separa el audio del video.
3. **Transcriber**: Convierte audio en texto (Whisper).
4. **Translator**: Traduce el texto (Argos).
5. **SubtitleGenerator**: Crea archivos `.vtt` y `.srt` con tiempos exactos.
6. **TTSEngine**: Genera la voz traducida si está habilitado.
7. **AudioMixer**: Mezcla la voz original balanceada con el doblaje.
8. **VideoMuxer**: Empaqueta el video + audio final + subtítulos en formato HLS.

## 🧠 Notas para Desarrolladores

- **Sincronización HLS**: Se utiliza una medición de duración exacta mediante `ffprobe` para evitar tirones en las uniones de los segmentos.
- **PipelineData**: Es el objeto central que viaja entre módulos conteniendo rutas de archivos y metadatos del chunk.
- **Hot Reload**: La configuración puede cambiarse mientras el stream corre sin perder la conexión SRT.
- **Seguridad**: El módulo `core/security.py` proporciona utilidades para sanitización de paths, validación de entrada y protección contra inyección de comandos.

### Añadir un nuevo módulo
Hereda de `BaseModule` en `core/module_base.py` e impleméntalo en la lista de `main.py`.
## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
python -m pytest tests/ -v

# Solo tests unitarios
python -m pytest tests/unit/ -v

# Solo tests de API
python -m pytest tests/unit/test_api_routes.py -v

# Tests con coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Estructura de Tests

```
tests/
├── conftest.py          # Fixtures compartidos
├── unit/                # Tests unitarios
│   ├── test_api_routes.py      # Tests de API REST (53 tests)
│   ├── test_config_manager.py  # Tests de configuración
│   ├── test_pipeline.py        # Tests del pipeline
│   ├── test_module_base.py     # Tests de módulos base
│   ├── test_ffmpeg_utils.py    # Tests de utilidades FFmpeg
│   └── test_ws_routes.py       # Tests de WebSockets
├── integration/         # Tests de integración
│   └── test_server.py
└── e2e/                 # Tests end-to-end
    ├── test_api_e2e.py
    ├── test_dashboard_page.py
    └── test_player_page.py
```

### Fixtures Disponibles

- `temp_dir`: Directorio temporal para tests
- `config_file`: Archivo de configuración de prueba
- `sample_srt_content`: Contenido SRT de ejemplo
- `mock_app_context`: Contexto de aplicación mockeado
- `client`: Cliente de test FastAPI

### Marcadores de Tests

- `@pytest.mark.slow`: Tests lentos (excluir con `-m "not slow"`)
- `@pytest.mark.integration`: Tests de integración
- `@pytest.mark.e2e`: Tests end-to-end
- `@pytest.mark.live`: Tests que requieren servidor activo

---

*Desarrollado con enfoque en baja latencia y máxima calidad visual.*
