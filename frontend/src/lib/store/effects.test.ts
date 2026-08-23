/**
 * Tests for effects.ts - DOM updates driven by signal changes.
 *
 * Tests verify that effects correctly update DOM elements when signals change.
 * Since effects use document.getElementById, we mock the DOM with jsdom-compatible elements.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// Mock DOM elements
function createMockEl(
  id: string,
  tag: string = "span",
  parent: HTMLElement | null = null,
): HTMLElement {
  const el = document.createElement(tag);
  el.id = id;
  if (parent) parent.appendChild(el);
  return el;
}

describe("effects - Status Effect", () => {
  let container: HTMLDivElement;
  let statusDot: HTMLSpanElement;
  let statusText: HTMLSpanElement;
  let btnStart: HTMLButtonElement;
  let btnStop: HTMLButtonElement;

  beforeEach(async () => {
    // Create mock DOM elements
    container = document.createElement("div");
    document.body.appendChild(container);

    statusDot = createMockEl(
      "status-dot",
      "span",
      container,
    ) as HTMLSpanElement;
    statusText = createMockEl(
      "status-text",
      "span",
      container,
    ) as HTMLSpanElement;
    btnStart = createMockEl(
      "btn-start",
      "button",
      container,
    ) as HTMLButtonElement;
    btnStop = createMockEl(
      "btn-stop",
      "button",
      container,
    ) as HTMLButtonElement;

    // Import signals and set initial state
    const { pipelineStatus, updateStatus } = await import("./signals");
    pipelineStatus.value = null;

    // Import and start effects
    const { startEffects, stopEffects } = await import("./effects");
    stopEffects();
    startEffects();

    // Give effects time to run
    await new Promise((r) => setTimeout(r, 50));
  });

  afterEach(async () => {
    document.body.innerHTML = "";

    const { stopEffects } = await import("./effects");
    stopEffects();

    // Reset signals
    const {
      pipelineStatus,
      pipelineLogs,
      throughputHistory,
      pipelineConfig,
      wsConnected,
      connectionMode,
    } = await import("./signals");
    pipelineStatus.value = null;
    pipelineConfig.value = null;
    pipelineLogs.value = [];
    throughputHistory.value = [];
    wsConnected.value = false;
    connectionMode.value = "local";
  });

  it("status dot shows stopped when pipeline is null", async () => {
    const { pipelineStatus } = await import("./signals");
    pipelineStatus.value = null;
    await new Promise((r) => setTimeout(r, 50));

    expect(statusText.textContent).toBe("APAGADO");
    expect(statusDot.classList.contains("running")).toBe(false);
    expect(statusDot.classList.contains("error")).toBe(false);
  });

  it("status shows ACTIVO and dot has running class when running", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({
      state: "running",
      chunks_processed: 0,
      modules: [],
    });
    await new Promise((r) => setTimeout(r, 50));

    expect(statusText.textContent).toBe("ACTIVO");
    expect(statusDot.classList.contains("running")).toBe(true);
    expect(statusDot.classList.contains("error")).toBe(false);
  });

  it("start button is disabled when running", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({
      state: "running",
      chunks_processed: 0,
      modules: [],
    });
    await new Promise((r) => setTimeout(r, 50));

    expect(btnStart.disabled).toBe(true);
    expect(btnStart.style.opacity).toBe("0.5");
    expect(btnStop.disabled).toBe(false);
    expect(btnStop.style.opacity).toBe("1");
  });

  it("start button is enabled when stopped", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({
      state: "stopped",
      chunks_processed: 0,
      modules: [],
    });
    await new Promise((r) => setTimeout(r, 50));

    expect(btnStart.disabled).toBe(false);
    expect(btnStart.style.opacity).toBe("1");
    expect(btnStop.disabled).toBe(true);
    expect(btnStop.style.opacity).toBe("0.5");
  });
});

// F162: Module indicators effect moved to ProcessGrid.astro (more comprehensive)
describe.skip("effects - Module Indicators", () => {
  let container: HTMLDivElement;

  beforeEach(async () => {
    container = document.createElement("div");
    document.body.appendChild(container);

    // Create indicator elements
    createMockEl("indicator-input", "span", container);
    createMockEl("indicator-whisper", "span", container);
    createMockEl("indicator-translate", "span", container);
    createMockEl("indicator-tts", "span", container);
    createMockEl("indicator-subtitle", "span", container);
    createMockEl("indicator-audio-mixer", "span", container);
    createMockEl("indicator-video-muxer", "span", container);
    createMockEl("status-dot", "span", container);
    createMockEl("status-text", "span", container);
    createMockEl("btn-start", "button", container);
    createMockEl("btn-stop", "button", container);
    createMockEl("pipeline-indicator", "span", container);

    const { pipelineStatus, updateStatus } = await import("./signals");
    pipelineStatus.value = null;

    const { startEffects, stopEffects } = await import("./effects");
    stopEffects();
    startEffects();
    await new Promise((r) => setTimeout(r, 50));
  });

  afterEach(async () => {
    document.body.innerHTML = "";
    const { stopEffects } = await import("./effects");
    stopEffects();
    const {
      pipelineStatus,
      pipelineLogs,
      throughputHistory,
      pipelineConfig,
      wsConnected,
      connectionMode,
    } = await import("./signals");
    pipelineStatus.value = null;
    pipelineConfig.value = null;
    pipelineLogs.value = [];
    throughputHistory.value = [];
    wsConnected.value = false;
    connectionMode.value = "local";
  });

  it("module indicators are inactive when pipeline is stopped", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({
      state: "stopped",
      chunks_processed: 0,
      modules: [
        {
          name: "transcriber",
          state: "idle",
          enabled: true,
          last_process_time_ms: 0,
          processed_chunks: 0,
        },
      ],
    });
    await new Promise((r) => setTimeout(r, 50));

    expect(
      document
        .getElementById("indicator-whisper")
        ?.classList.contains("active"),
    ).toBe(false);
  });

  it("module indicators are active when pipeline is running and module is enabled", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({
      state: "running",
      chunks_processed: 5,
      modules: [
        {
          name: "transcriber",
          state: "running",
          enabled: true,
          last_process_time_ms: 150,
          processed_chunks: 5,
        },
        {
          name: "translator",
          state: "idle",
          enabled: false,
          last_process_time_ms: 0,
          processed_chunks: 0,
        },
      ],
    });
    await new Promise((r) => setTimeout(r, 50));

    expect(
      document
        .getElementById("indicator-whisper")
        ?.classList.contains("active"),
    ).toBe(true);
    expect(
      document
        .getElementById("indicator-translate")
        ?.classList.contains("active"),
    ).toBe(false);
  });
});

describe("effects - System Metrics", () => {
  let container: HTMLDivElement;

  beforeEach(async () => {
    container = document.createElement("div");
    document.body.appendChild(container);

    // Create metric elements
    createMockEl("metric-cpu-bar", "div", container);
    createMockEl("metric-cpu-value", "span", container);
    createMockEl("metric-cpu", "div", container);
    createMockEl("metric-memory-bar", "div", container);
    createMockEl("metric-memory-value", "span", container);
    createMockEl("metric-memory-percent", "span", container);
    createMockEl("metric-memory", "div", container);
    createMockEl("metric-gpu-bar", "div", container);
    createMockEl("metric-gpu-value", "span", container);
    createMockEl("metric-gpu-memory", "span", container);
    createMockEl("metric-gpu", "div", container);
    createMockEl("metric-throughput-bar", "div", container);
    createMockEl("metric-throughput-value", "span", container);
    createMockEl("status-dot", "span", container);
    createMockEl("status-text", "span", container);
    createMockEl("btn-start", "button", container);
    createMockEl("btn-stop", "button", container);
    createMockEl("pipeline-indicator", "span", container);

    const { pipelineStatus, throughputHistory } = await import("./signals");
    pipelineStatus.value = null;
    throughputHistory.value = [];

    const { startEffects, stopEffects } = await import("./effects");
    stopEffects();
    startEffects();
    await new Promise((r) => setTimeout(r, 50));
  });

  afterEach(async () => {
    document.body.innerHTML = "";
    const { stopEffects } = await import("./effects");
    stopEffects();
    const {
      pipelineStatus,
      pipelineLogs,
      throughputHistory,
      pipelineConfig,
      wsConnected,
      connectionMode,
    } = await import("./signals");
    pipelineStatus.value = null;
    pipelineConfig.value = null;
    pipelineLogs.value = [];
    throughputHistory.value = [];
    wsConnected.value = false;
    connectionMode.value = "local";
  });

  it("CPU metric updates with status data", async () => {
    const { pipelineStatus } = await import("./signals");
    (pipelineStatus.value as any) = {
      state: "running",
      chunks_processed: 10,
      modules: [],
      uptime_seconds: 5,
      system_metrics: {
        cpu_percent: 45,
        memory_mb: 2048,
        memory_percent: 60,
        gpu_percent: 80,
        gpu_memory_mb: 4096,
        gpu_memory_usage: 50,
      },
    };
    pipelineStatus.value = { ...(pipelineStatus.value as any) };
    await new Promise((r) => setTimeout(r, 50));

    const cpuBar = document.getElementById("metric-cpu-bar") as HTMLDivElement;
    const cpuValue = document.getElementById(
      "metric-cpu-value",
    ) as HTMLSpanElement;
    expect(cpuBar.style.width).toBe("45%");
    expect(cpuValue.textContent).toBe("45%");
  });

  it("CPU metric shows warning class above 70%", async () => {
    const { pipelineStatus } = await import("./signals");
    (pipelineStatus.value as any) = {
      state: "running",
      chunks_processed: 10,
      modules: [],
      uptime_seconds: 5,
      system_metrics: {
        cpu_percent: 75,
        memory_mb: 2048,
        memory_percent: 60,
        gpu_percent: 0,
        gpu_memory_mb: 0,
        gpu_memory_usage: 0,
      },
    };
    pipelineStatus.value = { ...(pipelineStatus.value as any) };
    await new Promise((r) => setTimeout(r, 50));

    const cpuItem = document.getElementById("metric-cpu") as HTMLDivElement;
    expect(cpuItem.classList.contains("warning")).toBe(true);
    expect(cpuItem.classList.contains("critical")).toBe(false);
  });

  it("CPU metric shows critical class above 90%", async () => {
    const { pipelineStatus } = await import("./signals");
    (pipelineStatus.value as any) = {
      state: "running",
      chunks_processed: 10,
      modules: [],
      uptime_seconds: 5,
      system_metrics: {
        cpu_percent: 95,
        memory_mb: 2048,
        memory_percent: 60,
        gpu_percent: 0,
        gpu_memory_mb: 0,
        gpu_memory_usage: 0,
      },
    };
    pipelineStatus.value = { ...(pipelineStatus.value as any) };
    await new Promise((r) => setTimeout(r, 50));

    const cpuItem = document.getElementById("metric-cpu") as HTMLDivElement;
    expect(cpuItem.classList.contains("warning")).toBe(false);
    expect(cpuItem.classList.contains("critical")).toBe(true);
  });

  it("memory metric updates correctly", async () => {
    const { pipelineStatus } = await import("./signals");
    (pipelineStatus.value as any) = {
      state: "running",
      chunks_processed: 10,
      modules: [],
      uptime_seconds: 5,
      system_metrics: {
        cpu_percent: 30,
        memory_mb: 3072,
        memory_percent: 75,
        gpu_percent: 0,
        gpu_memory_mb: 0,
        gpu_memory_usage: 0,
      },
    };
    pipelineStatus.value = { ...(pipelineStatus.value as any) };
    await new Promise((r) => setTimeout(r, 50));

    const memBar = document.getElementById(
      "metric-memory-bar",
    ) as HTMLDivElement;
    const memValue = document.getElementById(
      "metric-memory-value",
    ) as HTMLSpanElement;
    const memPercent = document.getElementById(
      "metric-memory-percent",
    ) as HTMLSpanElement;
    expect(memBar.style.width).toBe("75%");
    expect(memValue.textContent).toBe("3072 MB");
    expect(memPercent.textContent).toBe("75%");
  });

  it("throughput metric updates from throughputAvg", async () => {
    const { throughputHistory } = await import("./signals");
    throughputHistory.value = [2.0, 3.0, 4.0]; // avg = 3.0
    await new Promise((r) => setTimeout(r, 50));

    const tpValue = document.getElementById(
      "metric-throughput-value",
    ) as HTMLSpanElement;
    expect(tpValue.textContent).toBe("3.00/s");
  });
});

// F162: Module metrics and GPU badges effects moved to ProcessGrid.astro
describe.skip("effects - Module Metrics", () => {
  let container: HTMLDivElement;

  beforeEach(async () => {
    container = document.createElement("div");
    document.body.appendChild(container);

    // Create module metric elements
    for (const name of [
      "transcriber",
      "translator",
      "tts_engine",
      "subtitle_generator",
      "audio_mixer",
      "video_muxer",
      "input",
    ]) {
      createMockEl(`module-time-${name}`, "span", container);
      createMockEl(`module-chunks-${name}`, "span", container);
      createMockEl(`module-encoder-${name}`, "span", container);
      createMockEl(`gpu-badge-${name}`, "span", container);
    }
    createMockEl("status-dot", "span", container);
    createMockEl("status-text", "span", container);
    createMockEl("btn-start", "button", container);
    createMockEl("btn-stop", "button", container);
    createMockEl("pipeline-indicator", "span", container);

    const { pipelineStatus, throughputHistory } = await import("./signals");
    pipelineStatus.value = null;
    throughputHistory.value = [];

    const { startEffects, stopEffects } = await import("./effects");
    stopEffects();
    startEffects();
    await new Promise((r) => setTimeout(r, 50));
  });

  afterEach(async () => {
    document.body.innerHTML = "";
    const { stopEffects } = await import("./effects");
    stopEffects();
    const {
      pipelineStatus,
      pipelineLogs,
      throughputHistory,
      pipelineConfig,
      wsConnected,
      connectionMode,
    } = await import("./signals");
    pipelineStatus.value = null;
    pipelineConfig.value = null;
    pipelineLogs.value = [];
    throughputHistory.value = [];
    wsConnected.value = false;
    connectionMode.value = "local";
  });

  it("module time shows -- when not running and no data", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({
      state: "stopped",
      chunks_processed: 0,
      modules: [
        {
          name: "transcriber",
          state: "idle",
          enabled: true,
          last_process_time_ms: 0,
          processed_chunks: 0,
        },
      ],
    });
    await new Promise((r) => setTimeout(r, 50));

    const timeEl = document.getElementById(
      "module-time-transcriber",
    ) as HTMLSpanElement;
    expect(timeEl.textContent).toBe("--");
  });

  it("module time shows actual last_process_time_ms", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({
      state: "running",
      chunks_processed: 5,
      modules: [
        {
          name: "transcriber",
          state: "running",
          enabled: true,
          last_process_time_ms: 250,
          processed_chunks: 5,
        },
      ],
    });
    await new Promise((r) => setTimeout(r, 50));

    const timeEl = document.getElementById(
      "module-time-transcriber",
    ) as HTMLSpanElement;
    expect(timeEl.textContent).toBe("250ms");
  });

  it("module time shows seconds when >= 1000ms", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({
      state: "running",
      chunks_processed: 5,
      modules: [
        {
          name: "transcriber",
          state: "running",
          enabled: true,
          last_process_time_ms: 1500,
          processed_chunks: 5,
        },
      ],
    });
    await new Promise((r) => setTimeout(r, 50));

    const timeEl = document.getElementById(
      "module-time-transcriber",
    ) as HTMLSpanElement;
    expect(timeEl.textContent).toBe("1.5s");
  });

  it("module chunks shows processed_chunks", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({
      state: "running",
      chunks_processed: 10,
      modules: [
        {
          name: "transcriber",
          state: "running",
          enabled: true,
          last_process_time_ms: 100,
          processed_chunks: 10,
        },
      ],
    });
    await new Promise((r) => setTimeout(r, 50));

    const chunksEl = document.getElementById(
      "module-chunks-transcriber",
    ) as HTMLSpanElement;
    expect(chunksEl.textContent).toBe("10");
  });

  it("GPU badge is visible when using_gpu is true", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({
      state: "running",
      chunks_processed: 5,
      modules: [
        {
          name: "transcriber",
          state: "running",
          enabled: true,
          last_process_time_ms: 100,
          processed_chunks: 5,
          extra: { using_gpu: true, device: "cuda" },
        },
      ],
    });
    await new Promise((r) => setTimeout(r, 50));

    const badge = document.getElementById(
      "gpu-badge-transcriber",
    ) as HTMLSpanElement;
    expect(badge.style.display).toBe("inline");
    expect(badge.classList.contains("active")).toBe(true);
  });

  it("GPU badge shows CPU when using_gpu is false", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({
      state: "running",
      chunks_processed: 5,
      modules: [
        {
          name: "transcriber",
          state: "running",
          enabled: true,
          last_process_time_ms: 100,
          processed_chunks: 5,
          extra: { using_gpu: false, device: "cpu" },
        },
      ],
    });
    await new Promise((r) => setTimeout(r, 50));

    const badge = document.getElementById(
      "gpu-badge-transcriber",
    ) as HTMLSpanElement;
    // When the module is enabled and explicitly on CPU, the badge stays
    // visible but shows "CPU" (no GPU class) so the user knows the module
    // is running but not on the accelerator.
    expect(badge.style.display).toBe("inline");
    expect(badge.textContent).toBe("CPU");
    expect(badge.classList.contains("active")).toBe(false);
  });
});

describe("effects - WS Status Badge", () => {
  let container: HTMLDivElement;
  let badge: HTMLDivElement;
  let label: HTMLSpanElement;

  beforeEach(async () => {
    container = document.createElement("div");
    document.body.appendChild(container);

    // Estructura real de layout/Header.astro
    badge = document.createElement("div");
    badge.id = "ws-status";
    badge.className = "ws-status disconnected";
    label = document.createElement("span");
    label.className = "ws-status-label";
    label.textContent = "WS OFF";
    badge.appendChild(label);
    container.appendChild(badge);

    createMockEl("status-dot", "span", container);
    createMockEl("status-text", "span", container);
    createMockEl("btn-start", "button", container);
    createMockEl("btn-stop", "button", container);
    createMockEl("pipeline-indicator", "span", container);

    const { wsConnected } = await import("./signals");
    wsConnected.value = false;

    const { startEffects, stopEffects } = await import("./effects");
    stopEffects();
    startEffects();
    await new Promise((r) => setTimeout(r, 50));
  });

  afterEach(async () => {
    document.body.innerHTML = "";
    const { stopEffects } = await import("./effects");
    stopEffects();
    const {
      pipelineStatus,
      pipelineLogs,
      throughputHistory,
      pipelineConfig,
      wsConnected,
      connectionMode,
    } = await import("./signals");
    pipelineStatus.value = null;
    pipelineConfig.value = null;
    pipelineLogs.value = [];
    throughputHistory.value = [];
    wsConnected.value = false;
    connectionMode.value = "local";
  });

  it("WS badge shows OFF when disconnected", async () => {
    const { wsConnected } = await import("./signals");
    wsConnected.value = false;
    await new Promise((r) => setTimeout(r, 50));

    expect(label.textContent).toBe("WS OFF");
    expect(badge.classList.contains("connected")).toBe(false);
    expect(badge.classList.contains("disconnected")).toBe(true);
  });

  it("WS badge shows ON when connected", async () => {
    const { wsConnected } = await import("./signals");
    wsConnected.value = true;
    await new Promise((r) => setTimeout(r, 50));

    expect(label.textContent).toBe("WS ON");
    expect(badge.classList.contains("connected")).toBe(true);
    expect(badge.classList.contains("disconnected")).toBe(false);
  });
});

describe("effects - Pipeline Indicator", () => {
  let container: HTMLDivElement;

  beforeEach(async () => {
    container = document.createElement("div");
    document.body.appendChild(container);

    createMockEl("pipeline-indicator", "span", container);
    createMockEl("status-dot", "span", container);
    createMockEl("status-text", "span", container);
    createMockEl("btn-start", "button", container);
    createMockEl("btn-stop", "button", container);

    const { pipelineStatus } = await import("./signals");
    pipelineStatus.value = null;

    const { startEffects, stopEffects } = await import("./effects");
    stopEffects();
    startEffects();
    await new Promise((r) => setTimeout(r, 50));
  });

  afterEach(async () => {
    document.body.innerHTML = "";
    const { stopEffects } = await import("./effects");
    stopEffects();
    const {
      pipelineStatus,
      pipelineLogs,
      throughputHistory,
      pipelineConfig,
      wsConnected,
      connectionMode,
    } = await import("./signals");
    pipelineStatus.value = null;
    pipelineConfig.value = null;
    pipelineLogs.value = [];
    throughputHistory.value = [];
    wsConnected.value = false;
    connectionMode.value = "local";
  });

  it("pipeline indicator is not active when stopped", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({ state: "stopped", chunks_processed: 0, modules: [] });
    await new Promise((r) => setTimeout(r, 50));

    const indicator = document.getElementById(
      "pipeline-indicator",
    ) as HTMLSpanElement;
    expect(indicator.classList.contains("active")).toBe(false);
  });

  it("pipeline indicator is active when running", async () => {
    const { updateStatus } = await import("./signals");
    updateStatus({ state: "running", chunks_processed: 5, modules: [] });
    await new Promise((r) => setTimeout(r, 50));

    const indicator = document.getElementById(
      "pipeline-indicator",
    ) as HTMLSpanElement;
    expect(indicator.classList.contains("active")).toBe(true);
  });
});

describe("effects - Remote Mode", () => {
  let container: HTMLDivElement;

  beforeEach(async () => {
    container = document.createElement("div");
    document.body.appendChild(container);

    createMockEl("remote-config", "div", container);
    createMockEl("btn-mode-local", "button", container);
    createMockEl("btn-mode-remote", "button", container);
    createMockEl("status-dot", "span", container);
    createMockEl("status-text", "span", container);
    createMockEl("btn-start", "button", container);
    createMockEl("btn-stop", "button", container);
    createMockEl("pipeline-indicator", "span", container);

    const { connectionMode } = await import("./signals");
    connectionMode.value = "local";

    const { startEffects, stopEffects } = await import("./effects");
    stopEffects();
    startEffects();
    await new Promise((r) => setTimeout(r, 50));
  });

  afterEach(async () => {
    document.body.innerHTML = "";
    const { stopEffects } = await import("./effects");
    stopEffects();
    const {
      pipelineStatus,
      pipelineLogs,
      throughputHistory,
      pipelineConfig,
      wsConnected,
      connectionMode,
    } = await import("./signals");
    pipelineStatus.value = null;
    pipelineConfig.value = null;
    pipelineLogs.value = [];
    throughputHistory.value = [];
    wsConnected.value = false;
    connectionMode.value = "local";
  });

  it("remote config is hidden in local mode", async () => {
    const { connectionMode } = await import("./signals");
    connectionMode.value = "local";
    await new Promise((r) => setTimeout(r, 50));

    const remoteConfig = document.getElementById(
      "remote-config",
    ) as HTMLDivElement;
    const btnLocal = document.getElementById(
      "btn-mode-local",
    ) as HTMLButtonElement;
    const btnRemote = document.getElementById(
      "btn-mode-remote",
    ) as HTMLButtonElement;
    expect(remoteConfig.style.display).toBe("none");
    expect(btnLocal.classList.contains("active")).toBe(true);
    expect(btnRemote.classList.contains("active")).toBe(false);
  });

  it("remote config is visible in remote mode", async () => {
    const { connectionMode } = await import("./signals");
    connectionMode.value = "remote";
    await new Promise((r) => setTimeout(r, 50));

    const remoteConfig = document.getElementById(
      "remote-config",
    ) as HTMLDivElement;
    const btnLocal = document.getElementById(
      "btn-mode-local",
    ) as HTMLButtonElement;
    const btnRemote = document.getElementById(
      "btn-mode-remote",
    ) as HTMLButtonElement;
    expect(remoteConfig.style.display).toBe("");
    expect(btnLocal.classList.contains("active")).toBe(false);
    expect(btnRemote.classList.contains("active")).toBe(true);
  });
});

describe("effects - startEffects and stopEffects", () => {
  it("startEffects does not throw", async () => {
    const { startEffects } = await import("./effects");
    expect(() => startEffects()).not.toThrow();
  });

  it("stopEffects does not throw", async () => {
    const { startEffects, stopEffects } = await import("./effects");
    startEffects();
    expect(() => stopEffects()).not.toThrow();
  });

  it("effects can be started and stopped multiple times", async () => {
    const { startEffects, stopEffects } = await import("./effects");
    startEffects();
    stopEffects();
    startEffects();
    stopEffects();
    startEffects();
    expect(() => stopEffects()).not.toThrow();
  });
});
