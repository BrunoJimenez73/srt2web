# Sesión actual — F101: Corrección de bugs frontend/backend ✅ DONE

## Bugs corregidos

### 1. ✅ Subtítulos se desajustan o desaparecen

**Causa raíz**: `subtitle_generator.py` en `configure()` sobreescribía defaults con valores muy agresivos:

- `_max_vtt_entries`: 2000 → 200 (5x menos)
- `_vtt_max_age_seconds`: 7200s (2h) → 300s (5min)
  Esto cortaba los subtítulos después de solo 5 minutos o 200 chunks.

**Fix**: Aumentado a 1000 entradas y 1800s (30min) como defaults. Agregado logging de los valores actuales.

### 2. ✅ Per-Module Latency sin formatear

**Causa raíz**: `MetricsCard.astro` usaba `innerHTML` en el effect de latency breakdown. Astro scopes CSS con data-attributes, pero los elementos creados con `innerHTML` no heredan esos atributos → el CSS no se aplicaba.

**Fix**: Reemplazado `innerHTML` con `createElement` + `className` (que sí respeta el scoping de Astro). También se añadió `:global()` a las reglas CSS de timing-stage como fallback.

### 3. ✅ Módulo traducir sin GPU

**Explicación**: El módulo Translator usa `argostranslate` que es CPU-only (traducción offline sin aceleración GPU). Esto es correcto y esperado.

**Fix**: El badge GPU ahora muestra "CPU" para módulos que corren en CPU, "GPU" para los que usan aceleración, y se oculta solo cuando el módulo no está activo. Antes se ocultaba para todos los que no tenían `using_gpu: true`.

### 4. ✅ Desplegable logs no funciona

**Causa raíz**: Dos sistemas de renderizado competían:

- `logpanel.ts` (DOM appendChild + filtros propios)
- Inline `<script>` en `LogPanel.astro` (virtual scroll + filtros propios)
  Ambos se inicializaban y configuraban event listeners DUPLICADOS. Cambiar el filtro en el dropdown o hacer toggle activaba respuestas impredecibles.

**Fix**: Eliminado el inline script duplicado con virtual scroll. Unificado todo en `logpanel.ts` que es el sistema principal. El inline script ahora solo maneja el evento de toggle (click en header) y clear logs, delegando a las funciones exportadas de logpanel.ts.

## Archivos modificados

- `frontend/src/components/LogPanel.astro` — eliminado virtual scroll duplicado
- `frontend/src/components/MetricsCard.astro` — innerHTML → createElement + :global() CSS
- `frontend/src/lib/modules/logpanel.ts` — fix dataset.level lowercase
- `frontend/src/lib/store/effects.ts` — GPU badges ahora muestran CPU/GPU correctamente
- `modules/subtitle_generator.py` — defaults aumentados: 1000 entradas, 30min rolling window
