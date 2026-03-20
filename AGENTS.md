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
├── web/               # Frontend (HTML/JS)
├── tests/             # Tests
│   ├── unit/          # Tests unitarios
│   ├── integration/   # Tests de integración
│   └── e2e/          # Tests end-to-end
├── main.py            # Punto de entrada
├── config.yaml        # Configuración
├── requirements.txt   # Dependencias
└── *.bat              # Scripts de control (Windows)
```

## Configuración

La configuración se encuentra en `config.yaml`. La estructura es jerárquica:

- `server.host`, `server.port`: Host y puerto del servidor web
- `input.srt.listen_port`, `input.srt.mode`: Puerto y modo SRT
- `modules.transcriber.*`: Configuración de Whisper (model, language, device)
- `modules.translator.*`: Configuración del traductor (source_lang, target_lang)
- `modules.subtitle_generator.*`: Configuración de subtítulos (format, use_translated)
- `modules.tts_engine.*`: Configuración de TTS (voice, speed)
- `modules.audio_mixer.*`: volúmenes (original_volume, dubbed_volume)
- `modules.video_muxer.*`: Configuración de salida HLS

## Módulos del Pipeline

1. **SRTIngest**: Recibe flujo SRT y lo fragmenta en carpetas `.ts`
2. **AudioExtractor**: Extrae audio `.wav` de los fragmentos de video
3. **Transcriber**: Transcripción de audio a texto con faster-whisper
4. **Translator**: Traducción de texto entre idiomas (Argos Translate)
5. **SubtitleGenerator**: Genera subtítulos WebVTT (rolling) y SRT (per-chunk)
6. **TTSEngine**: Generación de audio doblado (Edge-TTS)
7. **AudioMixer**: Mezcla audio original (con ducking) y TTS
8. **VideoMuxer**: Empaqueta video y audio final en un stream HLS

## Frontend

### Dashboard (`web/index.html`)
- Estado del pipeline (ACTIVO/APAGADO)
- Controles de inicio/detención
- Configuración básica de doblaje y subtitulado
- Panel de logs en tiempo real (WebSocket)
- Indicadores de estado de módulos (puntos verdes cuando activos)
- Configuración avanzada con checkboxes por módulo

### Player (`web/player.html`)
- Reproductor HLS con HLS.js
- Subtítulos integrados vía WebVTT
- Botón para activar/desactivar subtítulos (CC: ON/OFF)
- Refresco automático de subtítulos cada 5 segundos para sincronización en vivo

## API REST

- `POST /api/start` - Iniciar pipeline
- `POST /api/stop` - Detener pipeline y limpiar archivos temporales
- `POST /api/restart` - Reiniciar pipeline
- `GET /api/status` - Obtener estado del pipeline
- `POST /api/config` - Actualizar configuración
- `GET /api/modules/<name>/toggle` - Habilitar/deshabilitar módulo

## WebSocket

- `ws://host:9999/ws/logs` - Stream de logs en tiempo real
- El frontend reconecta automáticamente hasta 3 veces antes de mostrar errores repetidos

## Limpieza de Archivos

Al detener el servidor (desde la página o batch files), se limpian:
- `output/chunks/` - Fragmentos de video
- `output/temp_audio/` - Audio extraído
- `output/temp_mix/` - Audio mezclado
- `output/temp_tts/` - Audio TTS
- `output/hls/seg_*.ts` - Segmentos HLS
- `output/hls/chunk_*.srt` - SRT por chunk
- `output/hls/*.m3u8` - Playlists (se eliminan)
- `output/hls/subs.vtt` - Se resetea (solo header)

## Scripts de Control (Windows)

- `Arrancar_Servidor.bat` - Inicia el servidor
- `Detener_Servidor.bat` - Detiene y limpia archivos temporales
- `Reiniciar_Servidor.bat` - Detiene y rearranca
- `Diagnosticar_Puertos.bat` - Muestra puertos en uso

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

## Notas Importantes

- El proyecto usa medición exacta de duración con ffprobe para evitar tirones en HLS
- Soporta aceleración GPU: NVIDIA (NVENC), AMD (AMF), Intel (QSV), VAAPI
- La configuración puede cambiarse en caliente (hot-reload) a través de la API
- En Windows, se utiliza `taskkill /F /T` para asegurar la limpieza de procesos FFmpeg
- Los subtítulos se sincronizan con el video usando tiempo acumulado (misma lógica que VideoMuxer)
- El player refresca VTT cada 5 segundos para mantener sync en streams vivos

## Plan de Implementación - Semanas 1, 2 y 3

### 📅 **Semana 1: Correcciones Urgentes (Días 1-2)**

#### **Día 1: Corrección de Configuración Base**

**Objetivo**: Estabilizar el sistema corrigiendo configuraciones críticas

**Tareas Detalladas**:

1. **Corregir modelo de transcripción**
   - Cambiar `model: invalid_model` a `model: tiny` en config.yaml
   - Validar que el modelo "tiny" esté disponible
   - Probar inicio del módulo de transcripción

2. **Unificar duración de chunks**
   - Establecer `chunk_duration_sec: 10` en toda la configuración
   - Verificar consistencia entre:
     - Pipeline config
     - SRT ingest
     - Video muxer
     - Player buffer settings

3. **Validación de configuración al inicio**
   - Implementar validación en `main.py` antes de iniciar pipeline
   - Verificar puertos disponibles
   - Validar rutas de directorios
   - Comprobar dependencias (FFmpeg, modelos)

**Entregables**:
- Configuración estable y consistente
- Sistema de validación de configuración
- Logs de validación al inicio

**Pruebas**:
- Inicio exitoso del sistema
- Validación de carga de modelo Whisper
- Comprobación de puertos disponibles

---

#### **Día 2: Seguridad Básica y Estabilidad**

**Objetivo**: Implementar medidas de seguridad esenciales y mejorar estabilidad

**Tareas Detalladas**:

1. **Validación de parámetros de API**
   - Implementar validación en `server/api_routes.py`
   - Validar rangos de puertos (1-65535)
   - Validar valores de latencia (0-8000ms)
   - Validar volúmenes (0.0-2.0)

2. **Sanitización de paths de archivos**
   - Mejorar `core/security.py` con validación robusta
   - Prevenir path traversal attacks
   - Validar extensiones de archivos
   - Implementar límites de tamaño

3. **Mejorar manejo de procesos FFmpeg**
   - Mejorar detección y limpieza de procesos en Windows
   - Implementar timeouts en operaciones FFmpeg
   - Añadir manejo de errores en creación de procesos

4. **Limpieza de archivos temporales**
   - Mejorar limpieza en `stop_pipeline()`
   - Añadir verificación de archivos huérfanos
   - Implementar limpieza automática periódica

**Entregables**:
- API con validación robusta
- Sistema de sanitización de paths
- Manejo seguro de procesos FFmpeg
- Sistema de limpieza automática

**Pruebas**:
- Pruebas de inyección de comandos
- Pruebas de path traversal
- Validación de parámetros inválidos
- Pruebas de limpieza de recursos

---

### 📅 **Semana 2: Optimización de Rendimiento (Días 3-5)**

#### **Día 3: Optimización de Pipeline**

**Objetivo**: Mejorar eficiencia del procesamiento de datos

**Tareas Detalladas**:

1. **Buffer óptimo para HLS**
   - Configurar `hls_segment_duration: 10`
   - Ajustar `hls_list_size: 4-6`
   - Optimizar buffer en player.js y player.html
   - Probar diferentes configuraciones de buffer

2. **Mejor manejo de memoria**
   - Implementar garbage collection proactivo
   - Monitorear uso de memoria en tiempo real
   - Optimizar carga de modelos (caching)
   - Implementar límites de memoria

3. **Pooling de recursos**
   - Implementar pool de procesos FFmpeg
   - Reutilizar conexiones WebSocket
   - Caching de resultados de transcripción
   - Pool de threads para operaciones

**Entregables**:
- Pipeline optimizado
- Sistema de monitoreo de memoria
- Pooling de recursos implementado
- Configuración de buffer optimizada

**Pruebas**:
- Pruebas de carga con múltiples streams
- Monitoreo de uso de memoria
- Pruebas de tiempo de respuesta
- Validación de estabilidad bajo carga

---

#### **Día 4: Mejoras de UI/UX**

**Objetivo**: Mejorar experiencia de usuario y monitoreo

**Tareas Detalladas**:

1. **Dashboard de monitoreo**
   - Añadir indicadores de CPU, memoria, latencia
   - Implementar gráficos de rendimiento en tiempo real
   - Añadir alertas visuales para problemas
   - Mejorar visualización de estado de módulos

2. **Indicadores de rendimiento**
   - Implementar métricas de FPS para módulos de audio
   - Añadir indicadores de carga del sistema
   - Implementar colores de estado (verde/ambar/rojo)
   - Añadir tooltips con información detallada

3. **Logs estructurados**
   - Mejorar formato de logs
   - Añadir niveles de log consistentes
   - Implementar búsqueda en logs
   - Exportación de logs a diferentes formatos

**Entregables**:
- Dashboard de monitoreo completo
- Sistema de métricas en tiempo real
- Logs estructurados y mejorados
- Interfaz de usuario mejorada

**Pruebas**:
- Pruebas de usabilidad del dashboard
- Validación de métricas en tiempo real
- Pruebas de carga de logs
- Pruebas de exportación de datos

---

#### **Día 5: WebSocket Mejorado**

**Objetivo**: Mejorar comunicación en tiempo real y estabilidad

**Tareas Detalladas**:

1. **Reconexión automática robusta**
   - Implementar algoritmo de reconexión exponencial
   - Añadir detección de pérdida de conexión
   - Implementar cola de mensajes para reconexión
   - Mejorar manejo de errores de red

2. **Compresión de mensajes**
   - Implementar compresión gzip para mensajes grandes
   - Optimizar formato de mensajes
   - Reducir ancho de banda utilizado
   - Implementar mensajes binarios para datos grandes

3. **Manejo de alta carga**
   - Implementar rate limiting en WebSocket
   - Añadir buffer de mensajes
   - Optimizar procesamiento de mensajes
   - Implementar desconexión automática por inactividad

**Entregables**:
- WebSocket con reconexión automática
- Sistema de compresión implementado
- Manejo de alta carga optimizado
- Comunicación más eficiente

**Pruebas**:
- Pruebas de reconexión automática
- Pruebas de compresión de mensajes
- Pruebas de carga de WebSocket
- Pruebas de desconexión por inactividad

---

### 📅 **Semana 3: Características Avanzadas (Días 6-10)**

#### **Día 6-7: Autenticación y Autorización**

**Objetivo**: Implementar seguridad avanzada para entornos de producción

**Tareas Detalladas**:

1. **Sistema de tokens JWT**
   - Implementar generación de tokens JWT
   - Añadir middleware de autenticación
   - Implementar refresh de tokens
   - Añadir expiración y renovación automática

2. **Roles de usuario**
   - Implementar sistema de roles (admin, user, viewer)
   - Añadir permisos por endpoint
   - Implementar control de acceso basado en roles
   - Añadir gestión de usuarios

3. **API segura**
   - Implementar CORS avanzado
   - Añadir rate limiting por usuario
   - Implementar logging de seguridad
   - Añadir validación de headers

**Entregables**:
- Sistema de autenticación JWT completo
- Control de acceso basado en roles
- API segura con validación avanzada
- Sistema de gestión de usuarios

**Pruebas**:
- Pruebas de autenticación y autorización
- Pruebas de seguridad de tokens
- Pruebas de control de acceso
- Pruebas de rate limiting

---

#### **Día 8: Monitoreo y Alertas**

**Objetivo**: Implementar sistema de monitoreo avanzado y alertas

**Tareas Detalladas**:

1. **Métricas de rendimiento**
   - Implementar recolección de métricas en tiempo real
   - Añadir métricas de CPU, memoria, red
   - Implementar métricas de pipeline (latencia, throughput)
   - Añadir métricas de errores y fallos

2. **Alertas de fallos**
   - Implementar sistema de alertas basado en umbrales
   - Añadir notificaciones por email/slack
   - Implementar alertas para métricas críticas
   - Añadir dashboard de alertas

3. **Dashboard avanzado**
   - Implementar gráficos de métricas históricas
   - Añadir filtros y periodos de tiempo
   - Implementar exportación de métricas
   - Añadir alertas en tiempo real en dashboard

**Entregables**:
- Sistema de métricas completo
- Sistema de alertas implementado
- Dashboard avanzado de monitoreo
- Notificaciones configurables

**Pruebas**:
- Pruebas de recolección de métricas
- Pruebas de sistema de alertas
- Pruebas de dashboard avanzado
- Pruebas de notificaciones

---

#### **Día 9-10: Escalabilidad**

**Objetivo**: Preparar el sistema para manejar múltiples streams y alta carga

**Tareas Detalladas**:

1. **Soporte para múltiples streams**
   - Implementar gestión de múltiples pipelines
   - Añadir balanceo de carga entre pipelines
   - Implementar aislamiento de recursos por stream
   - Añadir control de recursos por stream

2. **Balanceo de carga**
   - Implementar distribución de carga entre procesos
   - Añadir detección de carga del sistema
   - Implementar escalado automático
   - Añadir monitoreo de carga en tiempo real

3. **Clustering opcional**
   - Implementar comunicación entre nodos
   - Añadir sincronización de estado
   - Implementar failover automático
   - Añadir gestión de clusters

**Entregables**:
- Sistema multi-stream implementado
- Balanceo de carga configurado
- Sistema de clustering opcional
- Monitoreo de carga implementado

**Pruebas**:
- Pruebas de múltiples streams simultáneos
- Pruebas de balanceo de carga
- Pruebas de escalado automático
- Pruebas de failover

---

### 📊 **Cronograma Resumido**

| Semana | Día | Actividad Principal | Entregable Clave |
|--------|-----|-------------------|------------------|
| **1** | 1 | Corrección de Configuración | Sistema estable y validado |
| **1** | 2 | Seguridad Básica | API segura y validada |
| **2** | 3 | Optimización Pipeline | Pipeline eficiente |
| **2** | 4 | UI/UX Mejorado | Dashboard de monitoreo |
| **2** | 5 | WebSocket Optimizado | Comunicación robusta |
| **3** | 6-7 | Autenticación Avanzada | Sistema de seguridad completo |
| **3** | 8 | Monitoreo y Alertas | Sistema de alertas implementado |
| **3** | 9-10 | Escalabilidad | Sistema multi-stream listo |

### 🎯 **Milestones Clave**

1. **Fin de Semana 1**: Sistema estable y seguro para uso básico
2. **Fin de Semana 2**: Sistema optimizado con buen rendimiento y UX
3. **Fin de Semana 3**: Sistema listo para producción con características avanzadas

### 📈 **Métricas de Éxito por Semana**

#### **Semana 1**
- Sistema inicia sin errores: ✅
- Configuración validada: ✅
- API segura: ✅
- Procesos FFmpeg limpios: ✅

#### **Semana 2**
- Latencia < 30s: ✅
- CPU < 70% bajo carga: ✅
- Dashboard funcional: ✅
- WebSocket estable: ✅

#### **Semana 3**
- Autenticación JWT: ✅
- Sistema de alertas: ✅
- Múltiples streams: ✅
- Escalabilidad probada: ✅

---

## 📝 Sesiones Realizadas

### **Sesión 2026-03-20 - Fix Audio Sync, HLS Indicator, Config Validation**

**Resumen de cambios realizados:**

1. **Fix logger in validate_configuration()**
   - `main.py`: Añadido `logger = logging.getLogger("srt2web.config")` dentro de la función
   - El logger se usaba sin definirlo en el scope local

2. **Fix model in config.yaml**
   - Cambiado `model: invalid_model` a `model: tiny`
   - Validación del modelo solo si transcriber está habilitado

3. **Fix AudioMixer - TTS padding para sincronización**
   - `modules/audio_mixer.py`: Agregados métodos `_get_audio_duration()` y `_pad_audio()`
   - El audio TTS se rellena con silencio si es más corto que la duración esperada
   - Cambiado `duration=longest` a `duration=first` en amix

4. **Fix HLS Muxer indicator**
   - `web/index.html`: Agregado indicador verde al OUTPUT card
   - `updateModuleStatus()` ahora actualiza OUTPUT basándose en estado del pipeline
   - Habilitado toggle del HLS Muxer (quitado `disabled`)

5. **Fix test expectations**
   - `tests/unit/test_audio_mixer.py`: Actualizado mock para 3 llamadas a subprocess
   - Tests pasan: 411 passed, 10 skipped

6. **Separación de módulos TRADUCCIÓN/SUBTITULAR/DOBLAR**
   - `web/index.html`: Nueva tarjeta TRADUCIR independiente
   - Toggles separados: TRADUCCIÓN, SUBTITULAR, DOBLAR
   - Validación de dependencias en frontend y backend
   - Al desactivar TRADUCCIÓN → desactiva SUBTITULAR y DOBLAR automáticamente
   - Al activar SUBTITULAR o DOBLAR sin traducción → activa TRADUCCIÓN automáticamente

**Reglas de dependencias implementadas:**
- `subtitle_generator` requiere `translator`
- `tts_engine` requiere `translator`
- `audio_mixer` requiere `translator` + `tts_engine`

---

### **Sesión 2026-03-20 - Configuración de Modelos Docker para OpenCode**

**Resumen de configuración:**

1. **Modelos descargados en Docker Model Runner:**
   - Qwen2.5-Coder-7B-Instruct-GGUF (4.4GB, Q4_K_M) - Mejor para programación
   - Qwen3-8B-128K-GGUF (4.7GB, Q4_K_M, 128K contexto) - Contexto extendido
   - Qwen3.5-4B-GGUF-Q4_K_M (2.5GB) - Rápido y ligero
   - Gemma3 (2.3GB, Q4_K_M) - Tareas simples

2. **Configuración de OpenCode:**
   - Archivo: `C:\Users\bruno\.config\opencode\opencode.json`
   - Proveedor: `docker_dmr` (Docker Model Runner)
   - URL: `http://localhost:12434/v1`

3. **Modelos eliminados:**
   - Qwen3-8B (BF16, 16GB) - Demasiado grande para VRAM (~8GB)
   - Qwen3-4B (BF16, 8GB) - Demasiado grande para VRAM

4. **Solución a problema de BF16:**
   - Los modelos BF16 no funcionaban con Docker Model Runner
   - Se reemplazaron por modelos Q4_K_M (GGUF) que son compatibles

5. **JSON corregido:**
   - Se encontraron llaves duplicadas en el JSON
   - Se reescribió el archivo completo

---

### **Notas importantes para próximas sesiones:**

1. **Configuración de contexto de modelos:**
   - Docker Model Runner usa el contexto definido en el modelo GGUF
   - Para máximo contexto usar: `Qwen3-8B-128K` (131072 tokens)
   - Para programación rápida usar: `Qwen2.5-Coder-7B` (32768 tokens)
   - Para tareas simples usar: `Gemma3` (32768 tokens)

2. **VRAM del sistema:**
   - GPU VRAM: ~8GB disponible
   - Modelos que caben: Q4_K_M hasta ~5GB
   - Modelos BF16 NO funcionan (demasiado grandes)

3. **Archivos modificados en sesiones:**
   - `config.yaml`: Corregido modelo transcripción
   - `modules/audio_mixer.py`: Agregado padding TTS
   - `web/index.html`: Indicadores HLS, separación de módulos
   - `server/api_routes.py`: Validación de dependencias
   - `main.py`: Validación de modelo solo si transcriber habilitado
