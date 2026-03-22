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
| `server/ws_routes.py` | Autenticación WebSocket + WebSocketRequest wrapper |
| `core/config_manager.py` | Host por defecto 127.0.0.1, rate_limit_rpm=60 |
| `main.py` | access_log=True habilitado |
| `config.yaml` | Nuevas opciones: auth_token, rate_limit_rpm, max_request_size_mb |
| `frontend/src/lib/api.ts` | Auth token en requests HTTP y WebSocket |

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
| `Header.astro` | Loading state + security toggle integrado |
| `LogPanel.astro` | Estado vacío, aria-live, role=log, búsqueda |
| `MetricsCard.astro` | role=meter, aria-valuenow |
| `ProcessGrid.astro` | role=region, aria-label |
| `BaseLayout.astro` | Skip-to-content link |
| `index.astro` | Loading states en handlers |

### Fase 4 - Optimizaciones ✅

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

### Fase 6 - Rediseño UI Seguridad ✅

| Archivo | Mejora |
|---------|--------|
| `Header.astro` | Botón "🔐 Secure OFF/ON" integrado en header |
| `index.astro` | Eliminó SecurityCard |
| `SecurityCard.astro` | **Eliminado** - funcionalidad movida al header |

**UI de seguridad rediseñada**:
```
┌─────────────────────────────────────────────────────────────────────┐
│ SRT2Web 0.4.0    📚 Docs  [WS OFF] [🔐 Secure OFF▾]  💾 Guardar  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Bugs Corregidos

| Bug | Causa | Solución |
|-----|-------|----------|
| WebSocket crash | FastAPI no pasa Request a WebSocket | `WebSocketRequest` wrapper |
| config.yaml inválido | `model: invalid_model` | Cambiado a `model: small` |
| CSP bloquea HLS | `media-src 'self'` restrictivo | Permitir `http://* https://*` |
| Player no carga | `Hls.ErrorTypes.ERROR_OTHER` no existe | Usar `!data.fatal` |
| "Esperando..." | No se ocultaba | Ocultar en `MANIFEST_PARSED` |
| srt_ingest None | Acceso sin verificar | `ctx.get('srt_ingest')` |

---

## Tests (102 tests pasando)

| Archivo | Tests | Tema |
|---------|-------|------|
| `tests/unit/test_security_middleware.py` | 19 | Seguridad |
| `tests/unit/test_performance_optimizations.py` | 14 | Rendimiento |
| `tests/unit/test_phase4_5_improvements.py` | 23 | Fases 4-5 |
| `tests/unit/test_config_validation.py` | 26 | Config |
| `tests/unit/test_player_websocket_fixes.py` | 20 | Player/WSS/CSP |

```bash
python -m pytest tests/unit/test_security_middleware.py tests/unit/test_performance_optimizations.py tests/unit/test_phase4_5_improvements.py tests/unit/test_config_validation.py tests/unit/test_player_websocket_fixes.py -v
```

---

## Commits en GitHub

| Hash | Descripción |
|------|-------------|
| `e372d23` | Config cleanup + remove SecurityCard |
| `791a740` | Redesign security UI - integrate into Header |
| `d54bd36` | Tests for player, WebSocket and CSP fixes |
| `6627be5` | Fix player HLS playback and CSP issues |
| `b139859` | Fix WebSocket auth |
| `ed69267` | Fase 1-3 |

---

## Comandos Útiles

```bash
# Ejecutar servidor
Arrancar_Servidor.bat

# Reconstruir frontend
cd frontend && npm run build:local

# Ejecutar tests
python -m pytest tests/unit/ -v
```

---

## Notas Importantes

### Seguridad
- Token se configura desde header (botón 🔐 Secure)
- WebSocket: `ws://host/ws/logs?token=xxx`
- OBS usa **SRT** (puerto 9000), NO WebSocket

### Frontend Build
- SIEMPRE reconstruir tras cambios: `cd frontend && npm run build:local`
- Copiar a server/static/

### HLS Player
- URL: `http://localhost:9999/player`
- Stream: `http://localhost:9999/hls/stream.m3u8`

---

## Pendientes

- [ ] Reemplazar gputil por pynvml
- [ ] Process pooling para FFmpeg
- [ ] Mejoras responsive design
- [ ] Keyboard shortcuts
