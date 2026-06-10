import { describe, expect, it, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { InspectorPanel } from "./InspectorPanel";
import type { GraphNodeData } from "../../lib/graph/serialize";

describe("InspectorPanel", () => {
  it("muestra el mensaje vacío cuando no hay nodo seleccionado", () => {
    const { container } = render(
      <InspectorPanel selected={null} onChange={() => {}} />,
    );
    expect(container.querySelector('[data-testid="inspector-empty"]')).toBeTruthy();
  });

  it("muestra mensaje de 'configurar fuera del grafo' para input", () => {
    const { container } = render(
      <InspectorPanel
        selected={{ kind: "input" } as GraphNodeData}
        onChange={() => {}}
      />,
    );
    expect(container.querySelector('[data-testid="inspector-no-config"]')).toBeTruthy();
  });

  it("muestra el mismo mensaje para output", () => {
    const { container } = render(
      <InspectorPanel
        selected={{ kind: "output" } as GraphNodeData}
        onChange={() => {}}
      />,
    );
    expect(container.querySelector('[data-testid="inspector-no-config"]')).toBeTruthy();
  });

  it("renderiza los campos del schema para transcriber", () => {
    const { container } = render(
      <InspectorPanel
        selected={
          {
            kind: "transcriber",
            moduleConfig: { enabled: true, model: "base", language: "es", device: "auto", beam_size: 5 },
          } as GraphNodeData
        }
        onChange={() => {}}
      />,
    );
    const inspector = container.querySelector('[data-testid="inspector-transcriber"]');
    expect(inspector).toBeTruthy();
    // Campos esperados: enabled, model, language, device, beam_size
    expect(container.querySelector('[data-testid="inspector-field-enabled"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="inspector-field-model"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="inspector-field-language"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="inspector-field-device"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="inspector-field-beam_size"]')).toBeTruthy();
  });

  it("renderiza el campo de volumen como input numérico para audio_mixer", () => {
    const { container } = render(
      <InspectorPanel
        selected={
          {
            kind: "audio_mixer",
            moduleConfig: { enabled: true, original_volume: 1.0, tts_volume: 0.8 },
          } as GraphNodeData
        }
        onChange={() => {}}
      />,
    );
    expect(container.querySelector('[data-testid="inspector-field-original_volume"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="inspector-field-tts_volume"]')).toBeTruthy();
  });

  it("emit onChange al cambiar el checkbox enabled", () => {
    const onChange = vi.fn();
    const { container } = render(
      <InspectorPanel
        selected={
          {
            kind: "transcriber",
            moduleConfig: { enabled: true, model: "base", language: "es", device: "auto", beam_size: 5 },
          } as GraphNodeData
        }
        onChange={onChange}
      />,
    );
    const cb = container.querySelector(
      '[data-testid="inspector-field-enabled"]',
    ) as HTMLInputElement;
    fireEvent.click(cb);
    expect(onChange).toHaveBeenCalledTimes(1);
    const newData = onChange.mock.calls[0][0] as GraphNodeData;
    expect(newData.moduleConfig?.enabled).toBe(false);
  });

  it("emit onChange al cambiar un select enum (model)", () => {
    const onChange = vi.fn();
    const { container } = render(
      <InspectorPanel
        selected={
          {
            kind: "transcriber",
            moduleConfig: { enabled: true, model: "base", language: "es", device: "auto", beam_size: 5 },
          } as GraphNodeData
        }
        onChange={onChange}
      />,
    );
    const sel = container.querySelector(
      '[data-testid="inspector-field-model"]',
    ) as HTMLSelectElement;
    fireEvent.change(sel, { target: { value: "large-v3" } });
    expect(onChange).toHaveBeenCalled();
    const newData = onChange.mock.calls[0][0] as GraphNodeData;
    expect((newData.moduleConfig as unknown as Record<string, unknown>).model).toBe("large-v3");
  });
});
