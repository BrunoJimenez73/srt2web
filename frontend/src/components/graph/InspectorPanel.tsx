/**
 * Panel inspector para el nodo seleccionado en el grafo.
 *
 * Renderiza un formulario auto-generado a partir del `configFields` del
 * `NodeDef` correspondiente. Tipos soportados:
 * - boolean: checkbox
 * - number: input numérico (con min/max/step si están definidos)
 * - string: input texto
 * - enum: select con las opciones definidas
 *
 * Para nodos `input` y `output` (cuya config se edita fuera del grafo),
 * muestra un mensaje informativo.
 */
import type { FieldDef } from "../../lib/graph/nodeCatalog";
import type { ModuleConfig } from "../../lib/types/api";
import type { GraphNodeData } from "../../lib/graph/serialize";
import { getNodeDef } from "../../lib/graph/nodeCatalog";

export interface InspectorPanelProps {
  selected: GraphNodeData | null;
  onChange: (next: GraphNodeData) => void;
}

function FieldRow({
  field,
  value,
  onUpdate,
}: {
  field: FieldDef;
  value: unknown;
  onUpdate: (v: unknown) => void;
}) {
  const id = `field-${field.key}`;
  const inputStyle: React.CSSProperties = {
    width: "100%",
    background: "var(--bg-surface)",
    color: "var(--text-prime)",
    border: "1px solid var(--border-dim)",
    borderRadius: "var(--radius-sm)",
    padding: "4px 8px",
    fontSize: 12,
    fontFamily: "var(--font-mono, monospace)",
  };
  const labelStyle: React.CSSProperties = {
    display: "block",
    fontSize: 11,
    color: "var(--text-sec)",
    marginBottom: 2,
    marginTop: 8,
  };

  if (field.type === "boolean") {
    return (
      <label htmlFor={id} style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8, fontSize: 12 }}>
        <input
          id={id}
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onUpdate(e.currentTarget.checked)}
          data-testid={`inspector-field-${field.key}`}
        />
        <span>{field.label}</span>
        {field.description ? (
          <span style={{ color: "var(--text-dim)", fontSize: 10 }} title={field.description}>
            ⓘ
          </span>
        ) : null}
      </label>
    );
  }
  if (field.type === "enum") {
    return (
      <div>
        <label htmlFor={id} style={labelStyle}>
          {field.label}
        </label>
        <select
          id={id}
          value={String(value ?? "")}
          onChange={(e) => onUpdate(e.currentTarget.value)}
          style={inputStyle}
          data-testid={`inspector-field-${field.key}`}
        >
          {field.options?.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>
    );
  }
  if (field.type === "number") {
    return (
      <div>
        <label htmlFor={id} style={labelStyle}>
          {field.label}
        </label>
        <input
          id={id}
          type="number"
          value={value === undefined || value === null ? "" : Number(value)}
          min={field.min}
          max={field.max}
          step={field.step ?? 1}
          onChange={(e) => {
            const raw = e.currentTarget.value;
            if (raw === "") {
              onUpdate(undefined);
              return;
            }
            const n = Number(raw);
            onUpdate(Number.isNaN(n) ? undefined : n);
          }}
          style={inputStyle}
          data-testid={`inspector-field-${field.key}`}
        />
      </div>
    );
  }
  return (
    <div>
      <label htmlFor={id} style={labelStyle}>
        {field.label}
      </label>
      <input
        id={id}
        type="text"
        value={String(value ?? "")}
        onChange={(e) => onUpdate(e.currentTarget.value)}
        style={inputStyle}
        data-testid={`inspector-field-${field.key}`}
      />
    </div>
  );
}

export function InspectorPanel({ selected, onChange }: InspectorPanelProps) {
  if (!selected) {
    return (
      <div
        style={{
          padding: 16,
          color: "var(--text-sec)",
          fontSize: 12,
          fontFamily: "var(--font-mono, monospace)",
        }}
        data-testid="inspector-empty"
      >
        Selecciona un nodo del grafo para editar su configuración.
      </div>
    );
  }
  const def = getNodeDef(selected.kind);
  if (def.configFields.length === 0) {
    return (
      <div
        style={{ padding: 16, color: "var(--text-sec)", fontSize: 12 }}
        data-testid="inspector-no-config"
      >
        <strong style={{ color: "var(--text-prime)" }}>{def.label}</strong>
        <p style={{ marginTop: 8 }}>{def.description}</p>
        <p style={{ marginTop: 8, fontStyle: "italic" }}>
          La configuración de este nodo se edita en el dashboard principal
          (sección {def.configLocation.kind === "input" ? "Input" : "Outputs"}).
        </p>
      </div>
    );
  }
  const cfg: ModuleConfig = selected.moduleConfig ?? { enabled: true };

  const updateField = (key: string, value: unknown) => {
    const next: ModuleConfig = { ...cfg, [key]: value };
    onChange({ ...selected, moduleConfig: next });
  };

  return (
    <div
      style={{
        padding: 16,
        fontSize: 12,
        fontFamily: "var(--font-mono, monospace)",
        color: "var(--text-prime)",
      }}
      data-testid={`inspector-${selected.kind}`}
    >
      <h3
        style={{
          fontSize: 13,
          fontWeight: 600,
          margin: 0,
          marginBottom: 4,
          color: "var(--text-prime)",
        }}
      >
        {def.label}
      </h3>
      <p style={{ color: "var(--text-sec)", margin: 0, marginBottom: 8 }}>
        {def.description}
      </p>
      <label
        style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}
      >
        <input
          type="checkbox"
          checked={Boolean(cfg.enabled)}
          onChange={(e) => updateField("enabled", e.currentTarget.checked)}
          data-testid="inspector-field-enabled"
        />
        <span>Habilitado</span>
      </label>
      {def.configFields.map((field) => (
        <FieldRow
          key={field.key}
          field={field}
          value={(cfg as unknown as Record<string, unknown>)[field.key]}
          onUpdate={(v) => updateField(field.key, v)}
        />
      ))}
    </div>
  );
}

export default InspectorPanel;
