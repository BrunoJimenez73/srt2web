/**
 * Barra de herramientas del editor de grafo.
 *
 * Acciones:
 * - Start / Stop del pipeline
 * - Save preset (pide nombre vía prompt nativo, luego POST /api/presets)
 * - Load preset (dropdown con los presets disponibles)
 * - Apply (PUT /api/config con el estado actual del grafo)
 * - Reset (recarga la config del backend y reconstruye el grafo)
 *
 * Los handlers se inyectan desde el padre (`PipelineGraph`) para mantener
 * la toolbar presentacional.
 */
import { useEffect, useState } from "react";

export interface PresetSummary {
  name: string;
  description?: string;
  built_in?: boolean;
}

export interface ToolbarProps {
  isPipelineRunning: boolean;
  isApplying: boolean;
  isDirty: boolean;
  onStart: () => void;
  onStop: () => void;
  onApply: () => void;
  onReset: () => void;
  onSavePreset: (name: string) => void;
  onLoadPreset: (name: string) => void;
}

const buttonStyle: React.CSSProperties = {
  background: "var(--bg-card)",
  color: "var(--text-prime)",
  border: "1px solid var(--border-dim)",
  borderRadius: "var(--radius-sm)",
  padding: "6px 12px",
  fontSize: 12,
  fontFamily: "var(--font-mono, monospace)",
  cursor: "pointer",
};

const primaryStyle: React.CSSProperties = {
  ...buttonStyle,
  background: "var(--accent)",
  borderColor: "var(--accent)",
  color: "var(--text-pure, #fff)",
};

const disabledStyle: React.CSSProperties = {
  ...buttonStyle,
  opacity: 0.5,
  cursor: "not-allowed",
};

export function Toolbar(props: ToolbarProps) {
  const {
    isPipelineRunning,
    isApplying,
    isDirty,
    onStart,
    onStop,
    onApply,
    onReset,
    onSavePreset,
    onLoadPreset,
  } = props;
  const [presets, setPresets] = useState<PresetSummary[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        // listPresets es un módulo existente que usa signals; aquí solo
        // necesitamos los nombres, así que hacemos una llamada directa.
        const res = await fetch("/api/presets", { credentials: "include" });
        if (!res.ok) return;
        const data = (await res.json()) as { presets?: PresetSummary[] };
        if (!cancelled && data.presets) setPresets(data.presets);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSave = () => {
    const name = window.prompt("Nombre del preset:");
    if (!name) return;
    if (presets.some((p) => p.name === name)) {
      setError(`Ya existe un preset con nombre "${name}"`);
      return;
    }
    setError(null);
    onSavePreset(name);
  };

  const handleLoad = () => {
    if (!selectedPreset) return;
    onLoadPreset(selectedPreset);
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 12px",
        background: "var(--bg-surface)",
        borderBottom: "1px solid var(--border-dim)",
        fontFamily: "var(--font-mono, monospace)",
        flexWrap: "wrap",
      }}
      data-testid="graph-toolbar"
    >
      {isPipelineRunning ? (
        <button
          type="button"
          onClick={onStop}
          style={buttonStyle}
          data-testid="btn-stop"
        >
          ⏹ Stop
        </button>
      ) : (
        <button
          type="button"
          onClick={onStart}
          style={primaryStyle}
          data-testid="btn-start"
        >
          ▶ Start
        </button>
      )}
      <button
        type="button"
        onClick={onApply}
        disabled={isApplying || !isDirty}
        style={isApplying || !isDirty ? disabledStyle : primaryStyle}
        data-testid="btn-apply"
        title={isDirty ? "Aplicar cambios al backend" : "Sin cambios pendientes"}
      >
        {isApplying ? "Aplicando…" : isDirty ? "Apply * " : "Apply"}
      </button>
      <button
        type="button"
        onClick={onReset}
        disabled={isApplying}
        style={isApplying ? disabledStyle : buttonStyle}
        data-testid="btn-reset"
      >
        ↺ Reset
      </button>
      <span style={{ width: 1, height: 24, background: "var(--border-dim)" }} />
      <button
        type="button"
        onClick={handleSave}
        disabled={isApplying}
        style={isApplying ? disabledStyle : buttonStyle}
        data-testid="btn-save-preset"
      >
        💾 Save preset
      </button>
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <select
          value={selectedPreset}
          onChange={(e) => setSelectedPreset(e.currentTarget.value)}
          style={{
            ...buttonStyle,
            padding: "4px 6px",
          }}
          data-testid="select-preset"
        >
          <option value="">— Load preset —</option>
          {presets.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name}
              {p.built_in ? " (built-in)" : ""}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={handleLoad}
          disabled={!selectedPreset || isApplying}
          style={!selectedPreset || isApplying ? disabledStyle : buttonStyle}
          data-testid="btn-load-preset"
        >
          Load
        </button>
      </div>
      {error ? (
        <span
          style={{ color: "var(--error)", fontSize: 11, marginLeft: 8 }}
          role="alert"
        >
          {error}
        </span>
      ) : null}
    </div>
  );
}

export default Toolbar;
