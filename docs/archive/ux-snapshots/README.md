# UX Snapshots Archive

Snapshots de la interfaz de usuario capturados durante pruebas manuales con
Playwright MCP entre el 13 y 24 de mayo de 2026.

## Contenido

### `2026-05-snapshots/`

Volcado completo del directorio `.playwright-mcp/` original:

- **`page-*.yml`** (16 archivos) — accessibility snapshots de páginas del
  dashboard en distintos momentos. Tamaños: 0 bytes (placeholders post-navigate)
  hasta ~18 KB (página completa del dashboard con módulos, métricas, etc).
- **`console-*.log`** (14 archivos) — logs de consola del browser durante
  sesiones de prueba. Tamaños: 137 bytes (vacío / sin warnings) hasta 180 KB
  (sesión completa con errores y warnings acumulados).
- **`page-2026-05-19T18-29-04-926Z.png`** (54 KB) — única captura de pantalla
  presente, del dashboard antes del refactor modular.
- **`snapshot-remote.yml`** (18 KB) — snapshot inicial remoto del dashboard.

### `2026-05-24-player-retry-snapshot.md`

Snapshot puntual del estado "Reintentar" del reproductor HLS, capturado el
24/05/2026 a las 00:58. Útil para reproducir el bug F104 de LogPanel y
referenciar el estado visual del player antes del fix.

## Contexto

Estos snapshots se generaron durante las sesiones de betatesting manual del
dashboard web y el player HLS. Sirven como:

1. **Línea base visual** para comparar refactors futuros del frontend.
2. **Documentación de bugs resueltos** — los snapshots muestran el estado
   exacto que el usuario veía cuando reportó un problema.
3. **Regression testing manual** — un humano puede diff entre snapshots
   antiguos y el estado actual del UI.

## Por qué está archivado y no en `tests/`

Los snapshots `.yml` son capturas ad-hoc de un humano con Playwright MCP, no
tests automatizados. Moverlos a `tests/` confundiría el discoverer de pytest.
`docs/archive/ux-snapshots/` deja claro que es histórico y solo de referencia.

## Mantenimiento

Los snapshots son inmutables. Si necesitas un snapshot actual del dashboard,
usa Playwright MCP directamente y guárdalo en una subcarpeta con fecha
(ej. `2026-06-snapshots/`).
