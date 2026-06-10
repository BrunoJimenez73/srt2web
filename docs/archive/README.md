# docs/archive/

Repositorio de material histórico que ya no se usa activamente pero se
conserva como referencia.

## Contenido

### `ux-snapshots/`

Snapshots de Playwright MCP del dashboard y player HLS, capturados entre
13-24/05/2026 durante betatesting manual. Ver `ux-snapshots/README.md`
para detalle.

- `2026-05-snapshots/` — 33 archivos: 16 page-*.yml, 14 console-*.log, 1
  screenshot, 1 snapshot-remote.yml, 1 placeholder.
- `2026-05-24-player-retry-snapshot.md` — snapshot puntual del player
  mostrando el estado "Reintentar".

### `helm-srt2web/`

Helm chart de Kubernetes archivado. F51 (despliegue K8s) quedó en estado
`pending` y nunca se completó. Ver `helm-srt2web/README.md` para las
razones del archivo y cómo reactivarlo si fuera necesario en el futuro.

- `chart/` — Chart completo con `Chart.yaml`, `values.yaml` y 8 templates.

## Por qué existe este directorio

Cuando se mueve código o configuración fuera del árbol activo (por ejemplo,
eliminar un chart de Helm que ya no se usa), a veces es útil conservarlo
para referencia histórica en lugar de borrarlo. `docs/archive/` es el lugar
canónico para ese material:

- **No se ejecuta ni se importa** desde el código activo.
- **No se documenta en el README principal** ni en el índice de features.
- **Sigue las convenciones de docs/** (Markdown, linkable desde MkDocs).
- **Inmutable** — no se actualiza, solo se añade o se archiva con un commit
  que explica por qué.

## Mantenimiento

| Acción | Resultado |
|---|---|
| Material nuevo de archivo | Crear subdirectorio aquí con `README.md` índice |
| Material que se reactiva | Mover de vuelta a su ubicación original con un commit que documente la reactivación |
| Material obsoleto sin valor | Borrar el subdirectorio entero con un commit que documente la decisión |

El directorio `docs/archive/` NO está excluido del build de MkDocs; los
archivos son legibles y linkeables. Si algún día crece mucho, se puede
añadir a `nav:` de `mkdocs.yml` con una sección dedicada.
