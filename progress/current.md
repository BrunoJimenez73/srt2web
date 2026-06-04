# Sesión actual — F108: Subtitle sync via HLS.js native track (no polling, no drift) ✅ DONE (2026-06-04)

## Diagnóstico (causa raíz, 3 capas)

### Capa 1 — Polling + wipe-and-replace (la principal)

`frontend/src/lib/modules/player.ts:191-242` hace un `setInterval(loadSubtitles, 2000)` y en cada poll:

1. `fetch("/subtitles/subs.vtt?_=...")`
2. parsea todos los cues con regex
3. `Array.from(track.cues).forEach(c => track.removeCue(c))` — **borrado TOTAL**
4. Para cada cue nuevo, `track.addCue(new VTTCue(...))` — **re-añadido TOTAL**

Esto produce:

- **Lag 0-2s oscilante**: el segmento N+1 de video llega al HLS player instantáneamente, pero la cue del chunk N+1 se publica al servidor al mismo tiempo, y el cliente tarda hasta 2s en enterarse. El usuario ve la imagen del chunk N+1 con el subtítulo del chunk N durante hasta 2s, después se auto-corrige.
- **Flicker visible**: la cue activa desaparece y vuelve a aparecer cada 2s. El ojo humano es muy sensible al flicker en texto.
- **Costo creciente**: la rolling window llega a 2000 cues (límite en `subtitle_generator.py:50`). Cada poll re-crea 2000 `VTTCue` objects. En una sesión de 30 min, el browser tiene miles de cues inútiles que ya pasaron.

### Capa 2 — `SubtitleSyncMonitor` es código muerto

- `core/subtitle_sync_monitor.py` define `check_sync(audio_ts_ms, subtitle_ts_ms)` que mide drift y devuelve un factor de corrección.
- `core/app_context.py:146-151` lo crea y lo asigna a `pipeline.subtitle_sync_monitor`.
- `server/routes/pipeline.py:71-95` lo lee para `/api/status` (solo lectura, sin acción).
- **Pero `check_sync()` no se llama en ningún sitio del path runtime**. El usuario puede poner `enable_drift_detection: true` en `config.yaml` y no pasa nada. El flag `enable_drift_detection` se ignora.

### Capa 3 — Crecimiento de drift por mtime correction (acumulativo)

`modules/inputs/srt_input.py:586-591` (y `rtmp_input.py`) ajustan `cumulative_duration` retroactivamente con deltas de mtime:

```python
prev_duration = current_mtime - self._last_chunk_mtime
prev_duration = max(0.5, min(prev_duration, self._chunk_duration * 2))
self._cumulative_duration += prev_duration - self._chunk_duration
```

Esto está acotado a `[0.5, 2 * chunk_duration]`, pero **se acumula con cada chunk**. En una sesión de 30 min con chunk_duration=10s, son 180 chunks. Si el mtime real es sistemáticamente 0.05s mayor que `chunk_duration`, la deriva acumulada es `0.05 × 180 = 9s`.

`cumulative_duration` se usa para:

- `output_ts_offset` del segmento (start PTS en el HLS stream)
- `chunk_start` de cada cue en subs.vtt

Ambos se derivan del mismo valor, así que **en teoría están en sync**. Pero el segmento HLS tiene un EXTINF fijo (= `chunk_duration`) y la cue usa el `cumulative_duration` real. Si la corrección mtime se acumula 9s, el segmento 180° tiene PTS=900s pero EXTINF=10s, mientras que la cue más reciente tiene `start=899s` y la `currentTime` del player en ese momento es también ~899s. Coinciden.

PERO: el HLS player computa `currentTime` de los frames decodificados, no del EXTINF. Cada frame tiene un PTS (proveniente de `output_ts_offset`), y la cues se comparan con este `currentTime`. Si la decodificación lleva un retardo de 200ms (común en navegadores con hardware lento), `currentTime` puede ir por detrás del PTS objetivo durante esa ventana. Tras 180 chunks × 200ms = 36s de retardo acumulado, el browser hace un "resync" (seeks forward). Ese seek puede dejar la cue activa con un desajuste de hasta 200ms.

## Diseño de la solución (F108)

### Backend

1. **`modules/subtitle_generator.py`** — escribir **per-chunk VTT fragments** con timestamps **media-relative**:

   ```
   output/subtitles/subs_seg_000000.vtt
   00:00:02.500 --> 00:00:05.000
   Hola mundo

   00:00:06.000 --> 00:00:08.500
   Adios
   ```

   Los cues son media-relative (0..chunk_duration). El HLS player sabe la duración del fragmento (EXTINF) y la suma cumulativa de EXTINFs de los fragments anteriores; convierte cada cue `00:00:02.5` en media time absoluto = `sum(EXTINF prev) + 2.5`.

2. **`modules/subtitle_generator.py`** — escribir **`subs.m3u8`** (HLS subtitle media playlist):

   ```
   #EXTM3U
   #EXT-X-VERSION:3
   #EXT-X-TARGETDURATION:10
   #EXT-X-MEDIA-SEQUENCE:0
   #EXTINF:10.000,
   subs_seg_000000.vtt
   #EXTINF:10.000,
   subs_seg_000001.vtt
   ```

   Esta es una **media playlist válida para HLS** que lista los fragments. HLS.js la trata como playlist, descarga fragments según avanza, los parsea, agrega los cues al `<track>` del video. El browser renderiza cada cue a su `currentTime` en el mismo time-base que el video. **Cero polling, cero lag, cero flicker**.

3. **`modules/subtitle_generator.py`** — mantener `subs.vtt` rolling para los consumidores legacy (`webrtc_engine.py`, `recording_output.py`).

4. **`modules/outputs/hls_output.py`** — cambiar master playlist: `URI="/subtitles/subs.m3u8"` en vez de `subs.vtt`.

5. **`core/subtitle_sync_monitor.py`** + **`core/app_context.py`** + **`core/unified_pipeline.py`** — wire el monitor: después de cada chunk, llamar `check_sync(audio_wall_clock_ms, first_cue_media_time_ms)` y propagar `sync_correction_factor` al `SubtitleGenerator`. Así el drift correction configurado por el usuario **funciona de verdad**.

### Frontend

`frontend/src/lib/modules/player.ts`:

- Eliminar `parseVTT`, `loadSubtitles`, `startSubtitlePolling`, `stopSubtitlePolling`.
- Después de `MANIFEST_PARSED`, si `hls.subtitleTracks.length > 0`, hacer `hls.subtitleTrack = 0` (activa la primera pista de subtítulos, que es la traducción por defecto).

### Tests

- **Backend unit tests** (`tests/unit/test_f108_subtitle_hls_sync.py`):
  - `subs_seg_NNNNNN.vtt` se crea con cues en media-relative time
  - `subs.m3u8` tiene `EXT-X-MEDIA-SEQUENCE` correcto y lista fragments en orden
  - `subs.m3u8` se sobreescribe atómicamente (atomic rename)
  - El master playlist del HLS output apunta a `/subtitles/subs.m3u8`
  - `subs.vtt` rolling sigue funcionando (no se rompe backward compat)
  - `SubtitleSyncMonitor.check_sync` se llama al menos una vez por chunk
  - `sync_correction_factor` se actualiza cuando drift > threshold
- **Frontend test** (`frontend/src/lib/modules/player-subtitles.test.ts`):
  - Mock hls.js, simular MANIFEST_PARSED con 1+ subtitle track
  - Verificar que `hls.subtitleTrack = 0` se llama
  - Verificar que NO se crea ningún `setInterval` para polling

## Próximos pasos

1. ✅ Documentado
2. ✅ Implementar backend: per-chunk fragments + subs.m3u8 en subtitle_generator.py
3. ✅ Conectar SubtitleSyncMonitor
4. ✅ Actualizar hls_output.py master playlist
5. ✅ Reescribir player.ts para usar HLS.js native
6. ✅ Tests
7. ✅ Verificación: init.ps1 -Quick + tsc + mypy

## Verificación final (F108 cerrado)

- **Backend tests** (`tests/unit/test_f108_subtitle_hls_sync.py`): **42/42 PASSED** en 1.5s
  - 7 tests `_write_hls_fragment` (media-relative timestamps, clamping, skip-empty)
  - 5 tests `_rewrite_hls_playlist` (vacío válido, orden, target_duration, atomic write, media_sequence)
  - 3 tests `_trim_hls_fragments` (rolling window + delete dropped files)
  - 3 tests `start()` cleanup (stale subs.m3u8, stale seg files, fragments registry)
  - 8 tests drift monitor wiring (almacenar, called-per-chunk, blend, clamp, exception, no-op)
  - 4 tests public API (`get_playlist_path`, `get_playlist_url`, init state)
  - 3 tests legacy `subs.vtt` compat (sigue produciéndose, timestamps absolutos, coexistencia)
  - 3 tests `_do_process` integration (artifact creation, rolling window, sin dangling refs)
  - 2 tests HLSOutput master playlist (subs.m3u8 preferred, subs.vtt fallback)
  - 1 test pre-create subs.m3u8
  - 3 tests configure() resets (cambio chunk_duration resetea, no-op si igual)
- **Frontend tests** (`frontend/src/lib/modules/player-subtitles.test.ts`): **18/18 PASSED**
  - 9 tests `activateFirstSubtitleTrack` (sin preferred lang, no tracks, exact, prefix, fallback, showSubtitles=false, closed-captions filter, no-type, allSubtitleTracks preference, idempotent)
  - 2 tests `getActiveSubtitleTrackId`
  - 2 tests `disableSubtitles`
  - 4 tests `onSubtitleTrackListChange` (callback, filter, unsubscribe, missing off)
- **Full frontend suite**: 201/201 passed en 5.21s
- **Backend full suite**: 1183 passed, 3 skipped, 4 xpassed (parallel xdist) en 26.26s
- **mypy --strict**: 0 errores en 91 archivos
- **tsc --noEmit**: 0 errores
- **ruff check** en F108 test: all checks passed
- **2 e2e test failures pre-existentes en main** (`test_links_to_hls_stream`, `test_subtitle_refresh_interval`): confirmado con `git stash` que fallan ANTES de F108 — references "master.m3u8"/"setInterval" en `server/static/player.html` que ya no está bundled, el test lee el HTML estático, no la source. No introducidos por F108.

## Cambios técnicos (resumen)

### Backend

- `modules/subtitle_generator.py`:
  - Estado HLS: `_hls_playlist_path`, `_hls_list_size=6`, `_hls_fragments: list[dict]`, `_drift_monitor`
  - `start()`: limpia `subs_seg_*.vtt` y `subs.m3u8` stale
  - `_write_hls_fragment(chunk_index, segments, duration)`: escribe fragment con cues media-relative (clamping `start>=0`, `end<=duration`, `end>=start`)
  - `_rewrite_hls_playlist()`: atomic write de `subs.m3u8` con `EXT-X-VERSION:3`, `EXT-X-TARGETDURATION=max(EXTINF)+1`, `EXT-X-MEDIA-SEQUENCE=first_chunk_index`
  - `_trim_hls_fragments()`: rolling window con borrado de archivos dropped
  - `set_drift_monitor(monitor)`, `get_playlist_path()`, `get_playlist_url()`
  - `_do_process()`: append a fragments, trim, rewrite, llama `_drift_monitor.check_sync` por chunk, aplica blend `0.7*old + 0.3*new` con clamp en `|deviation|>=0.5`
  - `configure()`: al cambiar `chunk_duration` resetea HLS fragments y reescribe playlist
- `modules/outputs/hls_output.py`:
  - Master playlist init: elige `subs.m3u8` si existe, `subs.vtt` fallback, pre-crea `subs.m3u8` vacío si no existe ninguno
  - `from pathlib import Path` añadido
  - `_update_manifest` también prefiere `subs.m3u8`
- `core/app_context.py`: `pipeline.get_module("subtitle_generator").set_drift_monitor(sync_monitor)` — wires el monitor que antes era código muerto

### Frontend

- `frontend/src/lib/modules/player-subtitles.ts` (NUEVO): helper con `HlsLike`/`SubtitleTrackDescriptor`/`ActivateOptions` types; `activateFirstSubtitleTrack` (preferred lang exact→prefix→first), `getActiveSubtitleTrackId`, `disableSubtitles`, `onSubtitleTrackListChange` (suscribe a `hlsSubtitleTracksUpdated`)
- `frontend/src/lib/modules/player.ts`: eliminado polling (`parseVTT`, `loadSubtitles`, `startSubtitlePolling`, `stopSubtitlePolling`); en MANIFEST_PARSED llama `activateFirstSubtitleTrack(hls, {preferredLang: "es"})`; suscribe `onSubtitleTrackListChange` para re-activar en cada re-parse del manifest; `disconnect()` desuscribe y llama `disableSubtitles`
