# SRT2Web - Estado del Proyecto

## Información General
- **Fecha sesión**: 2026-03-22
- **Versión**: 0.4.0
- **Repositorio**: https://github.com/BrunoJimenez73/srt2web

---

## Mejoras Implementadas

### Fase 1 - Seguridad Crítica ✅

| Archivo | Mejora |
|---------|--------|
| `server/security.py` | **Nuevo** - AuthMiddleware, RateLimiter, SecurityHeaders, RequestSizeLimit |
| `server/app.py` | Integra todos los middlewares de seguridad |
| `server/ws_routes.py` | Autenticación WebSocket con token via `?token=xxx` |
| `core/config_manager.py` | Host por defecto 127.0.0.1, rate_limit_rpm=60 |
| `main.py` | access_log=True habilitado |
| `config.yaml` | Nuevas opciones: auth_token, rate_limit_rpm, max_request_size_mb |
| `frontend/src/lib/api.ts` | Auth token en requests HTTP y WebSocket |
| `frontend/src/components/SecurityCard.astro` | **Nuevo** - UI configuración token |

**Configuración de seguridad**:
```yaml
server:
  host: 127.0.0.1          # Solo localhost por defecto
  auth_token: ''           # Token de autenticación (vacío = sin auth)
  rate_limit_rpm: 60       # Límite de requests por minuto
  max_request_size_mb: 1   # Tamaño máximo de request
```

### Fase 2 - Rendimiento ✅

| Archivo | Mejora |
|---------|--------|
| `modules/tts_engine.py` | asyncio.run() en vez de crear event loop nuevo |
| `modules/audio_mixer.py` | Cache de duración ffprobe (evita llamadas repetidas) |
| `modules/transcriber.py` | Usa ModelCache para Whisper |
| `modules/translator.py` | Usa ModelCache para Argos Translate |
| `core/model_cache.py` | Ahora se usa correctamente (singleton) |

### Fase 3 - UX/Accesibilidad ✅

| Archivo | Mejora |
|---------|--------|
| `StatusCard.astro` | Loading states, aria-labels |
| `Header.astro` | Loading state en botón guardar |
| `LogPanel.astro` | Estado vacío, aria-live, role=log |
| `MetricsCard.astro` | role=meter, aria-valuenow |
| `ProcessGrid.astro` | role=region, aria-label |
| `BaseLayout.astro` | Skip-to-content link |
| `index.astro` | Loading states en handlers |

### Fase 4 - Optimizaciones Adicionales ✅

| Archivo | Mejora |
|---------|--------|
| `server/app.py` | GZipMiddleware - compresión automática >1KB |
| `modules/subtitle_generator.py` | Rolling window VTT (max 50 entradas, 60s max age) |

### Fase 5 - UX Mejoras ✅

| Archivo | Mejora |
|---------|--------|
| `player.astro` | Error overlay con botón Reintentar |
| `index.astro` | Confirmación antes de detener pipeline |
| `LogPanel.astro` | Input de búsqueda para filtrar logs |

---

## Tests

### Archivos de Tests Creados

| Archivo | Tests | Tema |
|---------|-------|------|
| `tests/unit/test_security_middleware.py` | 19 | Seguridad |
| `tests/unit/test_performance_optimizations.py` | 14 | Rendimiento |
| `tests/unit/test_phase4_5_improvements.py` | 23 | Fases 4-5 |

**Total: 56 tests nuevos, todos pasando**

### Ejecutar Tests

```bash
# Todos los tests nuevos
python -m pytest tests/unit/test_security_middleware.py tests/unit/test_performance_optimizations.py tests/unit/test_phase4_5_improvements.py -v

# Tests específicos
python -m pytest tests/unit/test_security_middleware.py -v  # Seguridad
python -m pytest tests/unit/test_performance_optimizations.py -v  # Rendimiento
python -m pytest tests/unit/test_phase4_5_improvements.py -v  # Fases 4-5
```

---

## Commits en GitHub

| Hash | Descripción |
|------|-------------|
| `ed69267` | Fase 1-3 (Seguridad, Rendimiento, UX) |
| `ae0a8f2` | Fase 4-5 (Compresión, Rolling VTT, HLS, UX) |
| `09b46bd` | Tests para todas las mejoras |

---

## Comandos Útiles

```bash
# Ejecutar servidor
python main.py

# Ejecutar tests
python -m pytest tests/unit/ -v

# Verificar sintaxis
python -m py_compile <archivo.py>

# Git status
git status
git log --oneline -5
```

---

## Notas Importantes

### Seguridad
- El `auth_token` debe configurarse en `config.yaml` o via SecurityCard en el dashboard
- Si auth_token está vacío, el sistema funciona sin autenticación (backwards compatible)
- WebSocket requiere token via query param: `ws://host/ws/logs?token=xxx`

### Rendimiento
- ModelCache es singleton - los modelos se comparten entre módulos
- ffprobe cache usa mtime como key - invalida automáticamente si el archivo cambia
- TTS usa asyncio.run() - no necesita gestión manual de event loops

### VTT Rolling Window
- Máximo 50 entradas por defecto
- Máximo 60 segundos de antigüedad
- Configurable via `max_vtt_entries` y `vtt_max_age_seconds` en config

### HLS Player
- Muestra error overlay después de 3 intentos fallidos
- Botón "Reintentar" para reconectar
- Mensajes de error en español

---

## Próximas Mejoras Pendientes

- [ ] Reemplazar gputil por pynvml (deprecated)
- [ ] Process pooling para FFmpeg
- [ ] Cache de package index de Argos Translate
- [ ] Mejoras en responsive design mobile
- [ ] Keyboard shortcuts
