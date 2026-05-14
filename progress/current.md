# Sesión activa — 2026-05-14

**Estado:** F34 (CLI+TUI) completada con mejora de pantallas de módulos
**Iniciada:** 2026-05-14

## Resumen de cambios

### ModuleDetailScreen (pantalla de configuración de módulo)
- **Nuevo archivo:** `cli/tui/screens/module_detail.py`
- Pantalla completa de configuración de cada módulo
- Formulario dinámico con campos según tipo de módulo (8 módulos)
- Campos: type, model, language, device, voice, speed, engine, encoder, etc.
- Botones: Save, Toggle Enable, Back
- Atajos: Esc=Back, Enter=Save, T=Toggle

### TUIModuleCard mejorado
- Ahora clickeable (click abre ModuleDetailScreen)
- Focusable para navegación con teclado
- Más información: GPU badge, memory MB
- Bordes de foco cuando seleccionado

### TUIModuleGrid mejorado
- Navegable con teclas (focus por índice)
- Click en card → mensaje `ModuleSelected`
- `CARD_NAMES` exportado para uso en app.py

### SRT2WebTUI actualizado
- `_config_data` almacenado para pasar a ModuleDetailScreen
- `_last_module_index` para recordar último módulo seleccionado
- `_module_info_map` para lookup rápido
- Nuevo binding `m` para abrir módulo
- Nuevo handler `on_module_selected` maneja clicks
- `action_open_module` crea ModuleDetailScreen con info del módulo

### ModuleInfo importado
- Usado para construir `ModuleInfo` desde datos del API

## Archivos creados/modificados

| Archivo | Cambio |
|---------|--------|
| `cli/tui/screens/module_detail.py` | **NUEVO** — ModuleDetailScreen completo |
| `cli/tui/widgets/module_grid.py` | Mejorado — clickeable, focusable, GPU |
| `cli/tui/app.py` | Actualizado — module detail integration |
| `feature_list.json` | F34 completed_date=2026-05-14 |

## Verificación

- ✅ Import test: todos los módulos se importan sin errores
- ✅ 31 tests unit passing (test_cli_client.py + test_cli_commands.py)
- ✅ ModuleDetailScreen tiene schema para los 8 módulos
- ✅ ModuleInfo.from_dict() funciona correctamente

## Pendientes
- (ninguno para F34 — completado)