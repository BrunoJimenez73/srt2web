# Sesión activa — 2026-05-12

**Estado:** F15 COMPLETADA ✅
**Completada:** 2026-05-12 10:45

## Progreso de features

### Sesión 2026-05-12 — Análisis y plan de mejoras

Análisis completo del repositorio realizado. Áreas auditadas:

| Área           | Hallazgos principales                                                       |
| -------------- | --------------------------------------------------------------------------- |
| Rendimiento    | WS reconnect lineal (sin jitter), polling fijo, LogPanel sin virtual scroll |
| Estabilidad    | Piper sin heartbeat, sin degradación elegante de módulos no críticos        |
| Arquitectura   | module_interface.py deprecated aún presente, endpoints inline en api_routes |
| Mantenibilidad | mypy no strict, PARA BORRAR/ commiteada, archivos de log en git             |
| UI/UX          | Sin sparklines, sin presets, sin responsive móvil, sin export de logs       |
| Testing        | Cobertura frontend no medida, sin threshold de coverage configurado         |
| DevOps         | Docker layers subóptimas, sin healthcheck en docker-compose                 |

### Features creadas (F15–F29):

| ID  | Nombre                                | Prioridad recomendada |
| --- | ------------------------------------- | --------------------- |
| F29 | repo_hygiene_and_cleanup              | 1 — hacer primero     |
| F22 | cleanup_dead_code_final               | 2                     |
| F24 | mypy_strict_mode                      | 3                     |
| F15 | ws_resilience_and_adaptive_polling    | 4                     |
| F17 | piper_heartbeat_and_graceful_degrade  | 5                     |
| F20 | output_health_monitoring              | 6                     |
| F16 | logpanel_virtual_scroll_and_export    | 7                     |
| F21 | config_push_via_websocket             | 8                     |
| F23 | api_versioning_and_pydantic_responses | 9                     |
| F25 | frontend_test_coverage_80             | 10                    |
| F18 | metrics_sparklines_and_latency_meter  | 11                    |
| F19 | pipeline_presets_profiles             | 12                    |
| F26 | mobile_responsive_layout              | 13                    |
| F28 | docker_optimization_and_health        | 14                    |
| F27 | pipeline_dependency_graph             | 15                    |

## Implementación activa — F15: ws_resilience_and_adaptive_polling

### Acceptance criteria

1. WSClient usa exponential backoff: `delay = min(base * 2^attempt + random(0, 500ms), 30s)`
2. Polling: 10s cuando stopped, 3s cuando running, 1s en primeros 5s post-start
3. Auth vía header `Sec-WebSocket-Protocol` o subprotocolo (no query param)
4. Parámetros `maxReconnectAttempts` y `backoffBase` configurables en constructor
5. Test verifica reconnect events
6. wsConnected signal se pone false en primer intento fallido

### Archivos a tocar

- `frontend/src/lib/api.ts` (WSClient.attemptReconnect)
- `frontend/src/lib/modules/pipeline-control.ts` (polling interval)
- `frontend/src/lib/store/signals.ts` (wsConnected signal)
- `server/ws_routes.py` (auth por subprotocolo)
- `frontend/src/lib/api.test.ts` (tests)

### Estado actual

- [x] init.ps1 verde (pytest instalado)
- [x] Cambiar F15 a in_progress
- [x] Modificar api.ts con exponential backoff + authToken
- [x] Modificar pipeline-control.ts con polling adaptivo
- [x] Modificar ws_routes.py para auth por mensaje inicial
- [x] wsConnected se pone false en primer intento fallido
- [x] Tests agregados (125 tests frontend pasan)
- [x] Build frontend OK
- [x] F15 marcada como done en feature_list.json
