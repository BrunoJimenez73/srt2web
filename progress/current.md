# Sesión activa — 2026-05-18

**Estado:** F71 + F72 + F73 completadas — Fix encoder persistence + GPU + API route
**Iniciada:** 2026-05-18

## Diagnóstico inicial

Análisis de logs y código:

- 24 archivos de log revisados (principal: `logs/srt2web.log` — sin errores críticos)
- 4 bugs críticos identificados en encoder persistence y GPU
- 1 bug crítico adicional: frontend llama a `PUT /config/video_muxer` que no existía

## Feature completada — F71

**Fix encoder mode persistence across configure/reconfigure API**

### Cambios F71

| Archivo                                     | Cambio                                                                                                 |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `modules/video_muxer.py:53-67`              | `configure()` ahora lee `encoder_mode` y recrea `EncoderConfig` cuando cambia                          |
| `modules/outputs/composite_output.py:46-65` | Nuevo método `configure_outputs(config_manager)` que reconfigura todos los output sinks                |
| `core/unified_pipeline.py:933-944`          | `reconfigure()` ahora también llama a `configure_outputs` en el output sink                            |
| `server/routes/config.py:219-231`           | `POST /api/config/chunk` ya no resetea `encoder_mode` a `passthrough` — preserva la config del usuario |
| `core/constants.py:154`                     | `ALLOWED_ENCODER_MODES` actualizado con valores reales de `EncoderModeEnum`                            |
| `core/types.py:58-67`                       | `EncoderMode` marcado como `DEPRECATED` — usar `EncoderModeEnum` de `config_schema.py`                 |
| `tests/unit/test_config_validation.py:72`   | `VALID_ENCODER_MODES` sincronizado con `EncoderModeEnum` (se agregó `gpu_videotoolbox`)                |
| `feature_list.json`                         | F71 añadida como `done`                                                                                |

### Verificación F71

| Check                                            | Resultado      |
| ------------------------------------------------ | -------------- |
| `pytest tests/unit/ -q --tb=short -m "not slow"` | ✅ 100% passed |
| `mypy core/ server/ --strict`                    | ✅ 0 errores   |
| `init.ps1 -Quick`                                | ✅ Verde       |

## Feature completada — F72

**GPU acceleration for VIDEOMUXER and OUTPUT modules**

### Cambios F72

| Archivo                                                | Cambio                                                                                                                                 |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| `core/encoder_config.py:55`                            | Default `gpu_preset` cambiado de `p3` a `p7` (coherente con `config.yaml`)                                                             |
| `core/encoder_config.py:141-157`                       | Nuevos métodos: `get_gpu_videotoolbox_args()` y `get_gpu_vaapi_args()`                                                                 |
| `core/ffmpeg_utils.py:134`                             | `check_gpu_support()` ahora incluye `videotoolbox` en el dict de resultados                                                            |
| `core/ffmpeg_utils.py:153`                             | `check_gpu_support()` detecta `h264_videotoolbox` y `hevc_videotoolbox`                                                                |
| `core/ffmpeg_utils.py:505`                             | `check_videotoolbox_support()` ahora lee `stderr + stdout` (no solo `stdout`)                                                          |
| `modules/outputs/hls_output.py:55`                     | `_gpu_info` incluye `vaapi` y `videotoolbox`                                                                                           |
| `modules/outputs/hls_output.py:343-356`                | `_get_encoder_config()` maneja `gpu_videotoolbox` y `gpu_vaapi`                                                                        |
| `modules/outputs/hls_output.py:466-472,494-502`        | `get_status()` maneja `gpu_videotoolbox` y `gpu_vaapi` correctamente                                                                   |
| `modules/video_muxer.py:39`                            | `_gpu_info` incluye `videotoolbox`                                                                                                     |
| `modules/video_muxer.py:140-216`                       | Nuevo método `_get_encoder_config()` + `_do_process()` ahora usa FFmpeg con encoder GPU cuando configurado (fallback a copia si falla) |
| `modules/video_muxer.py:374,406`                       | `get_status()` maneja `gpu_videotoolbox`                                                                                               |
| `modules/outputs/webrtc_output.py:30,47,97-104`        | Conectado `EncoderConfig`, `get_status()` reporta `encoder_mode` real desde config                                                     |
| `modules/outputs/recording_output.py:60`               | `_gpu_info` incluye `vaapi` y `videotoolbox`                                                                                           |
| `tests/unit/test_video_muxer.py:63,88`                 | Mocks actualizados con `videotoolbox`                                                                                                  |
| `tests/unit/test_gpu_installer_restructure.py:132,164` | Mocks actualizados + `test_default_values` espera `p7`                                                                                 |
| `feature_list.json`                                    | F72 añadida como `done`                                                                                                                |

### Verificación F72

| Check                                            | Resultado      |
| ------------------------------------------------ | -------------- |
| `pytest tests/unit/ -q --tb=short -m "not slow"` | ✅ 1063 passed |
| `mypy core/ server/ --strict`                    | ✅ 0 errores   |
| `init.ps1 -Quick`                                | ✅ Verde       |

## Feature completada — F73

**Fix missing PUT /config/video_muxer API route + Fix opus audio crash**

### Problema 1: Ruta faltante

El frontend `HlsCard.astro` llamaba a `PUT /config/video_muxer` con valores planos como `{encoder_mode: "gpu_nvenc", video_crf: 18, ...}`, pero ese endpoint **no existía** en el servidor. La llamada recibía un 404 y el cambio de encoder se perdía silenciosamente.

Además, `CompositeOutput.configure_outputs()` solo pasaba `output.hls.*` a `HLSOutput.configure()`, pero los campos de encoder (`video_crf`, `gpu_preset`, `audio_codec`, etc.) no existen en `WebOutputConfig`. Nunca llegaban al `EncoderConfig`.

### Problema 2: Opus + MPEG-TS = crash FFmpeg

Aún cuando el encoder_mode se configuraba correctamente a `gpu_nvenc`, el `audio_codec: opus` en `config.yaml` hacía que FFmpeg fallara con:

```
ERROR FFmpeg mux error: [aost#0:1/opus] Could not open encoder before EOF
Nothing was written into output file
```

**El códec Opus no es compatible con el contenedor MPEG-TS** usado en HLS. Cada chunk fallaba, no se escribían segmentos `.ts`, y el reproductor mostraba "Error de red".

### Cambios F73

| Archivo                                     | Cambio                                                                                                                   |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `server/routes/config.py:182-236`           | Nueva ruta `PUT /config/video_muxer` que recibe keys planas y las mapea a `modules.video_muxer.*` + `output.{hls,web}.*` |
| `modules/outputs/composite_output.py:53-78` | `configure_outputs()` ahora mergea `modules.video_muxer.*` dentro del config que pasa a cada output sink                 |
| `modules/outputs/hls_output.py:233-245`     | Al generar args de audio para MPEG-TS, overridea `opus` → `aac` automáticamente                                          |
| `feature_list.json`                         | F73 añadida como `done`                                                                                                  |

### Flujo corregido

```
HlsCard.astro → PUT /config/video_muxer {encoder_mode: "gpu_nvenc", video_crf: 18, ...}
  ↓
server mapea a modules.video_muxer.* + output.hls.encoder_mode
  ↓
config.save() → reload() → pipeline.reconfigure()
  ↓
CompositeOutput.configure_outputs() mergea modules.video_muxer + output.hls
  ↓
HLSOutput.write() overridea audio_codec opus → aac para MPEG-TS
  ↓
FFmpeg: h264_nvenc + aac → segmentos .ts válidos → player OK
```

## Estado actual del proyecto

- ✅ 73 features completadas en `feature_list.json`
- ✅ `init.ps1 -Quick` pasa verde
- ✅ mypy 0 errores en core/ y server/
- ✅ Todos los cambios verificados con tests
