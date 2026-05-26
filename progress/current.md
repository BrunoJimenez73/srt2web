# Sesión actual — F100: Seguridad scripts Start/Stop y gestión de procesos ✅ DONE

## Cambios realizados

### 1. ✅ Start.bat — PID file

- Reemplazado `start` command por `PowerShell Start-Process -PassThru` para capturar PID
- Escribe PID en `srt2web.pid` en la raíz del proyecto
- Fallback al `start` tradicional si falla la captura

### 2. ✅ Stop.bat — Parada selectiva + --clean

- Lee PID de `srt2web.pid` y mata solo ese proceso con `taskkill /PID /T /F`
- Si no hay PID file, busca por puertos conocidos (9999, 9000, etc.)
- **Eliminado**: `taskkill /F /IM python.exe` global (mataba todos los python del sistema)
- **Eliminado**: `taskkill /F /IM node.exe` global
- **Eliminado**: `taskkill /F /IM ffmpeg.exe` global
- Limpieza de logs/output/caches movida a flag `--clean` con confirmación
- `Stop.bat` (sin args) solo mata procesos srt2web, no toca archivos

### 3. ✅ start_Mac.sh — Background + PID file + trap

- Servidor ahora corre en background con `&`
- Captura PID via `$!`, escribe `srt2web.pid`
- `trap cleanup EXIT` elimina PID file al salir

### 4. ✅ stop_Mac.sh — Parada selectiva + --clean

- Prioridad: leer PID de `srt2web.pid`
- Fallback: pgrep/lsof para TUI y servidor
- `--clean` flag con confirmación para limpieza

### 5. ✅ pipeline.py — Validación output_dir

- `stop_pipeline()` resuelve `output_dir` a path absoluto
- Verifica que esté dentro del project root antes de `shutil.rmtree`
- Si está fuera, loggea warning y retorna sin limpiar

### 6. ✅ Tests — 10 nuevos en TestProcessManagementSafety

- `test_stop_bat_no_global_taskkill_python/node/ffmpeg`
- `test_stop_bat_has_pid_file_logic`
- `test_stop_bat_has_clean_flag`
- `test_start_bat_writes_pid_file`
- `test_start_mac_sh_writes_pid_file`
- `test_stop_mac_sh_reads_pid_file`
- `test_stop_mac_sh_has_clean_flag`
- `test_pipeline_cleanup_validates_output_dir`

## Resultados

- `pytest tests/unit/ -n=4 -m "not slow"` → **1085 passed, 3 skipped, 4 xpassed** (+10 tests vs F98)
- `pytest tests/cli/ -q -n=2` → 192 passed
- feature_list.json: F99 añadido (build/static/docs/Docker), F100 marcado done

## Archivos modificados

- `Start.bat` — PID capture via PowerShell
- `Stop.bat` — reescrito: PID-based kill + --clean flag
- `start_Mac.sh` — background, PID file, trap cleanup
- `stop_Mac.sh` — reescrito: PID-based kill + --clean flag
- `server/routes/pipeline.py` — output_dir validation before rmtree
- `tests/unit/test_workspace_fixes.py` — 10 nuevos tests F100
- `feature_list.json` — F99 añadido y F100 marcado done
