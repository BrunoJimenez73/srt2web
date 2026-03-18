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

## 🚨 **Fallos y Problemas Detectados**

### 1. **Configuración Incorrecta**
- **Problema**: El archivo `config.yaml` tiene un modelo de transcripción inválido: `model: invalid_model`
- **Impacto**: El módulo de transcripción fallará al iniciar
- **Ubicación**: `config.yaml` línea 30

### 2. **Problemas de Seguridad**
- **Input Validation**: Falta validación robusta en varios endpoints de la API
- **Path Traversal**: No hay sanitización de rutas en operaciones de archivos
- **Command Injection**: Posible riesgo en llamadas a FFmpeg sin sanitización completa

### 3. **Problemas de Rendimiento**
- **Chunk Duration Mismatch**: Configuración de 6s vs 15s en diferentes partes del sistema
- **Memory Leaks**: Posibles fugas en manejo de procesos FFmpeg
- **Resource Cleanup**: No siempre se limpian archivos temporales correctamente

### 4. **Problemas de Estabilidad**
- **WebSocket Reconnections**: Lógica de reconexión limitada
- **Error Handling**: Falta manejo de errores en varios módulos
- **Process Management**: No siempre se matan procesos FFmpeg en Windows

## 🚀 **Plan de Implementación - 3 Semanas**

### **Semana 1: Correcciones Urgentes (Días 1-2)**

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

### **Semana 2: Optimización de Rendimiento (Días 3-5)**

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

### **Semana 3: Características Avanzadas (Días 6-10)**

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

### **Cronograma Resumido**

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

### **Milestones Clave**

1. **Fin de Semana 1**: Sistema estable y seguro para uso básico
2. **Fin de Semana 2**: Sistema optimizado con buen rendimiento y UX
3. **Fin de Semana 3**: Sistema listo para producción con características avanzadas

### **Métricas de Éxito por Semana**

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

## 🛠️ **Implementación Gradual**

Recomiendo implementar estas mejoras de forma incremental:

1. **Semana 1**: Correcciones urgentes y seguridad básica
2. **Semana 2**: Optimización de rendimiento y estabilidad
3. **Semana 3**: Características avanzadas y monitoreo
4. **Semana 4**: Pruebas, documentación y preparación para producción

## 📊 **Prioridades de Implementación**

### **Prioridad Alta (Semana 1)**
- Corrección de modelo de transcripción
- Validación de parámetros de API
- Sanitización de paths de archivos
- Mejor manejo de procesos FFmpeg

### **Prioridad Media (Semana 2)**
- Optimización de buffer HLS
- Dashboard de monitoreo
- WebSocket mejorado
- Logs estructurados

### **Prioridad Baja (Semana 3)**
- Autenticación JWT
- Sistema de alertas
- Escalabilidad multi-stream
- Clustering opcional

## 🔄 **Flujo de Trabajo Recomendado**

1. **Desarrollo**: Implementar en rama feature por funcionalidad
2. **Pruebas**: Testear cada cambio individualmente
3. **Integración**: Unir cambios a main después de pruebas exitosas
4. **Despliegue**: Deployar a entorno de staging para validación
5. **Producción**: Deployar a producción después de validación final

## 📈 **Métricas de Monitoreo**

### **Rendimiento**
- Latencia de procesamiento < 30s
- Uso de CPU < 70% bajo carga normal
- Uso de memoria estable sin leaks
- Tiempo de respuesta de API < 500ms

### **Disponibilidad**
- Tiempo de actividad > 99.9%
- Tiempo de recuperación ante fallos < 30s
- Reconexión automática de WebSocket < 5s
- Limpieza de recursos automática

### **Seguridad**
- 0 vulnerabilidades críticas
- Validación de entrada 100%
- Logs de seguridad completos
- Acceso restringido a recursos

## 🚨 **Consideraciones de Seguridad**

### **Prioridad Alta**
- Validación de entrada en todos los endpoints
- Sanitización de comandos FFmpeg
- Protección contra ataques DoS
- Autenticación básica

### **Prioridad Media**
- HTTPS/TLS para producción
- Rate limiting
- Logging de seguridad
- Validación de archivos subidos

### **Prioridad Baja**
- Auditoría de seguridad completa
- Escaneo de vulnerabilidades
- Hardening del sistema

## ⚡ **Optimizaciones de Rendimiento**

### **Inmediatas**
- Buffer HLS óptimo (8-10s)
- Modelo Whisper "tiny" para menor CPU
- Chunk duration 10s para mejor sincronización

### **Medio Plazo**
- GPU acceleration detection mejorado
- Caching de resultados
- Compresión de datos

### **Largo Plazo**
- Distribución de carga
- Microservicios opcionales
- CDN para assets estáticos

## 📋 **Checklist de Implementación**

### **Semana 1 - Correcciones Urgentes**
- [ ] Corregir modelo de transcripción en config.yaml
- [ ] Unificar duración de chunks en todo el sistema
- [ ] Implementar validación de configuración al inicio
- [ ] Validar parámetros de API (puertos, latencia, volúmenes)
- [ ] Mejorar sanitización de paths de archivos
- [ ] Mejorar manejo de procesos FFmpeg
- [ ] Implementar limpieza automática de archivos temporales

### **Semana 2 - Optimización de Rendimiento**
- [ ] Configurar buffer óptimo para HLS
- [ ] Implementar mejor manejo de memoria
- [ ] Implementar pooling de recursos
- [ ] Crear dashboard de monitoreo
- [ ] Añadir indicadores de rendimiento
- [ ] Mejorar logs estructurados
- [ ] Implementar reconexión automática robusta de WebSocket
- [ ] Implementar compresión de mensajes
- [ ] Mejorar manejo de alta carga en WebSocket

### **Semana 3 - Características Avanzadas**
- [ ] Implementar sistema de tokens JWT
- [ ] Crear roles de usuario (admin, user, viewer)
- [ ] Implementar API segura con validación avanzada
- [ ] Implementar métricas de rendimiento en tiempo real
- [ ] Crear sistema de alertas basado en umbrales
- [ ] Desarrollar dashboard avanzado de monitoreo
- [ ] Implementar soporte para múltiples streams
- [ ] Crear balanceo de carga entre procesos
- [ ] Implementar clustering opcional

## 🎯 **Próximos Pasos**

1. **Iniciar con Semana 1**: Comenzar por las correcciones urgentes
2. **Validar cada cambio**: Asegurar que cada implementación funciona correctamente
3. **Documentar avances**: Mantener registro de cambios y pruebas realizadas
4. **Preparar para producción**: Configurar entornos de staging y producción
5. **Monitorear continuamente**: Implementar monitoreo continuo del sistema

---

**Nota**: Este plan está diseñado para ser implementado de forma incremental, permitiendo validaciones parciales y correcciones tempranas. Cada semana debe concluir con un sistema funcional y estable que sirva como base para la siguiente fase.