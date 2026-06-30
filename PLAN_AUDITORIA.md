# Plan de auditoría — Calidad de código y subtítulos

> Generado el 2026-06-30 tras revisión exhaustiva del proyecto.
> Sigue las reglas del harness: una feature a la vez, init.ps1 verde para declarar done.

---

## Resumen ejecutivo

Se encontraron **~30 issues** agrupados en **7 nuevas features**. Lo más crítico:

1. **F173 (CRÍTICO)**: `player-subtitles.ts` NUNCA se importa en `player.ts`. F108/F167 quedaron incompletos. El sistema de subtítulos nativos de HLS.js no está conectado.
2. **F174 (ALTA)**: El `<track>` legacy + `startSubtitleRefresh` (polling cada 5s) sigue siendo la ÚNICA ruta activa de subtítulos. Hay doble renderizado potencial.
3. **F175 (ALTA)**: Código muerto confirmado: `subtitleWatchdog` en player.ts, `_hls_fragments` duplicado en subtitle_generator.py.
4. **F176 (MEDIA)**: 39 errores de ruff, 12 errores de mypy (producción), 14 warnings de ESLint.
5. **F177 (BAJA)**: Strings hardcodeadas, falta de i18n, tipado mejorable.

---

## Features propuestas

### F173 — CRÍTICO: Conectar player-subtitles.ts al player real

**Problema**: `player-subtitles.ts` (F108) se creó con funciones `activateFirstSubtitleTrack()`, `forceSubtitleTrackMode()`, `disableSubtitles()` pero **nunca se importó** en `player.ts`. grep confirma cero imports en código de producción. El helper existe, tiene tests (18), pero está huérfano.

**Qué hacer**:

- Importar `activateFirstSubtitleTrack` en `player.ts` y llamarlo en `MANIFEST_PARSED`
- Importar `forceSubtitleTrackMode` en `player.ts` y llamarlo en `SUBTITLE_TRACK_LOADED` y `LEVEL_UPDATED` (workaround bug HLS.js `mode="hidden"`)
- Importar `disableSubtitles` en `player.ts` y llamarlo en `disconnect()`
- Eliminar `startSubtitleRefresh` / `stopSubtitleRefresh` (el polling legacy)
- Eliminar el `<track id="subtitle-track">` de `player.astro` (ya no es necesario)

**Archivos**: `frontend/src/lib/modules/player.ts`, `frontend/src/pages/player.astro`

**Tests**: 18 tests existentes en `player-subtitles.test.ts` deben seguir pasando. Añadir tests de integración en player.test.ts.

**Riesgo**: Alto. Cambia la ruta de renderizado de subtítulos. Verificar que no hay doble subtítulo ni pérdida de cues.

---

### F174 — ALTA: Eliminar ruta dual de subtítulos legacy

**Problema**: Aunque F167 dice "Unificar renderizado de subtítulos (eliminar dual path)", el código legacy sigue activo:

- `player.astro:21`: `<track id="subtitle-track">` con `src="/subtitles/subs.vtt"`
- `player.ts:372-391`: `startSubtitleRefresh()` refresca ese track cada 5s via `setInterval`
- Esto compite con la ruta nativa de HLS.js (si F173 se implementa)

**Qué hacer**:

- Eliminar `<track>` de `player.astro`
- Eliminar `startSubtitleRefresh`, `stopSubtitleRefresh`, `subtitleRefreshInterval` de `player.ts`
- Verificar en `player.astro` y HTML estático que no queden referencias

**Archivos**: `frontend/src/pages/player.astro`, `frontend/src/lib/modules/player.ts`

**Depende de**: F173 (primero conectar la ruta nueva, luego eliminar la vieja)

**Riesgo**: Medio. Si F173 no se implementa primero, los subtítulos se pierden por completo.

---

### F175 — ALTA: Eliminar código muerto duplicado

**Problema**: mypy --strict reporta `subtitle_generator.py:53: error: Attribute "_hls_fragments" already defined on line 51` — la línea 53 es una duplicación exacta de la 51. Además `subtitleWatchdog` se declara en player.ts línea 105 pero nunca se usa (ESLint warning).

**Qué hacer**:

1. Eliminar línea 53 duplicada en `subtitle_generator.py`
2. Eliminar declaración `subtitleWatchdog` en `player.ts:105`
3. Buscar más código huérfano: `DEFAULTS` (pipeline-control.ts:55), `collectConfigFromUI` (pipeline-control.ts:68), `outputType` (config-collector.ts:33), `isLoading` (presets-client.ts:22), `resetThroughput` (ws-manager.ts:8), `signal`/`connectionUrls`/`inputFileChk`/`inputRtmpChk` (input-card.ts:1-23), `ModuleName`/`ModuleState` (signals.ts:13-15)
4. Verificar si `index.astro` es legacy vs `index_new.astro`

**Archivos**: `modules/subtitle_generator.py`, `frontend/src/lib/modules/player.ts`, `frontend/src/lib/modules/pipeline-control.ts`, `frontend/src/lib/modules/config-collector.ts`, `frontend/src/lib/modules/presets-client.ts`, `frontend/src/lib/modules/ws-manager.ts`, `frontend/src/lib/components/input-card.ts`, `frontend/src/lib/store/signals.ts`, `frontend/src/pages/index.astro`

**Tests**: Ejecutar `python -m pytest tests/unit/test_f108_subtitle_hls_sync.py` (42 tests), `npx tsc --noEmit`, `npm run lint`.

**Riesgo**: Bajo. Cambios mecánicos sin impacto funcional.

---

### F176 — MEDIA: Correcciones de linters (ruff + mypy + ESLint)

**Problema**: 39 errores ruff, 12 errores mypy (7 en webrtc_engine.py), 14 warnings ESLint.

**Qué hacer**:

**Ruff (39 errores)**:

- 23x `UP042` `str, Enum` → `StrEnum`: `CircuitState`, `PipelineModeEnum`, `DeviceEnum`, `ModelSizeEnum`, `LanguageEnum`, `InputTypeEnum`, `OutputTypeEnum`, `EncoderModeEnum`, `SubtitleFormatEnum`, `TTSEngineEnum`, `AudioCodecEnum`, `VideoCodecEnum`, `HardwareType`, `ErrorSeverity`, `ErrorCategory`, `PipelineMode`, `PipelineState`, `ModuleState`, `LogLevel`, `InputType`, `OutputType`, `DeviceType`, `EncoderMode`
- 4x `E402`: Mover imports al tope en `mediamtx_manager.py`, `security.py`, `routes/modules.py`, `routes/outputs.py`
- 4x `E721`: Usar `isinstance()` en `module_detail.py:108,210,219,221`
- 3x `SIM103`: Simplificar returns booleanos en `pipeline_error_handler.py:252`, `pipeline_validator.py:277`, `security.py:408`
- 2x `RUF022`: Ordenar `__all__` en `core/__init__.py` y `core/pipeline/__init__.py`
- 1x `RUF034`: Simplificar `if-else` identico en `ffmpeg_utils.py:230`
- 1x `RUF046`: Eliminar `int()` redundante en `hls_output.py:382`
- 1x `UP041`: `asyncio.TimeoutError` → `TimeoutError` en `unified_pipeline.py:503`

**Mypy (12 errores, 5 propios)**:

- `subtitle_generator.py:53`: Eliminar línea duplicada (cubierto en F175)
- `webrtc_engine.py:227,243,247,326,407,420`: 6 errores de tipado serio (Any, untyped decorator, unused ignore). Requiere refactor.
- `core/paths.py:163`: Instalar stubs `types-platformdirs` o `pip install platformdirs-stubs`
- `core/hardware_monitor.py:5`, `core/module_base.py:50`: Instalar `types-psutil`
- `core/unified_pipeline.py:18`: Instalar `types-psutil`

**ESLint (14 warnings)**:

- Eliminar variables no usadas listadas en F175
- Reemplazar `console.log` con logger en `logger.ts:34,39`

**Archivos**: Múltiples en core/, modules/, server/, cli/tui/, frontend/

**Tests**: `ruff check core/ modules/ server/ cli/ --fix`, `python -m mypy --strict modules/ core/ server/`, `npm run lint`.

**Riesgo**: Medio. Mayormente cambios mecánicos. webrtc_engine.py requiere atención por ser código sensible.

---

### F177 — BAJA: Internazionalización y tipado

**Problema**: Strings hardcodeadas en español/inglés sin abstracción i18n.

**Qué hacer**:

- Extraer strings de `ModuleNode.tsx` (status labels: "Inactivo", "Corriendo", etc.)
- Extraer strings de `InspectorPanel.tsx` ("Input", "Outputs")
- Extraer strings de `index_new.astro` (lenguajes, botones)
- En `subtitle_generator.py`: reemplazar `Any` con tipos concretos (`list[dict[str, float | str]]`, `SubtitleEntry`, etc.)
- En `subtitle_generator.py`: `set_drift_monitor(monitor: Any)` → `set_drift_monitor(monitor: SubtitleSyncMonitor | None)`
- Definir `SubtitleEntry = TypedDict` o dataclass para entries de VTT

**Archivos**: `frontend/src/components/graph/ModuleNode.tsx`, `frontend/src/components/graph/InspectorPanel.tsx`, `frontend/src/pages/index_new.astro`, `modules/subtitle_generator.py`, `core/subtitle_sync_monitor.py`

**Riesgo**: Bajo.

---

### F178 — BAJA: Monolítico subtitle_generator.py (631 líneas)

**Problema**: `subtitle_generator.py` tiene 631 líneas y 5 responsabilidades distintas:

1. Rolling VTT window management
2. HLS fragment generation + playlist management
3. Pipeline delay compensation
4. Drift correction integration
5. Dual track support

**Qué hacer**: Extraer a módulos más pequeños:

- `subtitle_generator/vtt_manager.py` — rolling window, rewrite, trim
- `subtitle_generator/hls_manager.py` — fragment writing, playlist rewrite, trim
- `subtitle_generator/delay_compensator.py` — pipeline delay estimator
- `subtitle_generator/__init__.py` — SubtitleGenerator orchestrator

**Archivos**: Nuevos bajo `modules/subtitle_generator/`

**Riesgo**: Alto. Refactor con impacto en tests. Posponer hasta después de F173-F176.

---

## Orden de implementación sugerido

```
F173 ──→ F174 ──→ F175 ──→ F176 ──→ F177 ──→ F178
  │         │         │         │         │
  │         │         │         │         └── Baja prioridad
  │         │         │         │
  │         │         │         └── Medio (linters + stubs)
  │         │         │
  │         │         └── Alta (dead code)
  │         │
  │         └── Alta (depende de F173)
  │
  └── Crítico (subtítulos rotos)
```

**Dependencias críticas**:

- F174 BLOQUEADO por F173 (no eliminar polling legacy sin conectar la alternativa nativa)
- F175 puede ir en paralelo con F173 (no overlapping)
- F176 independiente, puede ir en paralelo
- F177 independiente, puede ir en paralelo
- F178 después de todo lo demás

---

## Archivos tocados por feature

| Feature | Archivos                         | Líneas aprox    |
| ------- | -------------------------------- | --------------- |
| F173    | `player.ts`, `player.astro`      | ~50             |
| F174    | `player.ts`, `player.astro`      | ~40             |
| F175    | 9 archivos                       | ~30             |
| F176    | ~35 archivos                     | ~200            |
| F177    | 5 archivos                       | ~80             |
| F178    | 4 archivos nuevos + 1 modificado | ~650 (refactor) |

---

## Métricas de verificación

- `npx tsc --noEmit` → 0 errores
- `npm run lint` → 0 errors, 0 warnings
- `ruff check core/ modules/ server/ cli/` → 0 errores
- `python -m mypy --strict modules/ core/ server/` → 0 errores (stubs instalados)
- `python -m pytest tests/unit/test_f108_subtitle_hls_sync.py -q` → 42 pass
- `python -m pytest tests/unit/test_subtitle_generator.py -q` → 2 pass
- `python -m pytest tests/unit/test_subtitle_sync_monitor.py -q` → 4 pass
- `cd frontend && npm test` → todos pasan
- **Sin regresiones** en tests existentes
