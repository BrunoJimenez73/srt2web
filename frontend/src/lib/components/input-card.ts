import { signal, effect } from "@preact/signals-core";
import { connectionUrls, inputType } from "../store/index";

/**
 * InputCard - Módulo de lógica para el componente InputCard.
 * Centraliza toda la interacción del usuario y reactividad del card de entrada.
 * No depende de `dashboard.ts` ni usa `window.*`.
 */

// --- Elementos del DOM (se inicializan cuando el componente monta) ---
let inputTypeSelect: HTMLSelectElement | null = null;
let srtSettings: HTMLElement | null = null;
let rtmpSettings: HTMLElement | null = null;
let fileSettings: HTMLElement | null = null;
let rtmpUrlInput: HTMLInputElement | null = null;
let rtmpPortInput: HTMLInputElement | null = null;
let rtmpAppInput: HTMLInputElement | null = null;
let rtmpKeyInput: HTMLInputElement | null = null;
let btnCopyRtmp: HTMLButtonElement | null = null;
let fileSelectInput: HTMLInputElement | null = null;
let fileSelectBtn: HTMLButtonElement | null = null;
let inputFileChk: HTMLInputElement | null = null;
let inputRtmpChk: HTMLInputElement | null = null;

/**
 * Inicializa las referencias al DOM.
 * Debe llamarse una vez después de que el DOM esté listo.
 */
export function initInputCard(): void {
  inputTypeSelect = document.getElementById("input-type") as HTMLSelectElement;
  srtSettings = document.getElementById("input-srt-settings");
  rtmpSettings = document.getElementById("input-rtmp-settings");
  fileSettings = document.getElementById("input-file-settings");

  rtmpUrlInput = document.getElementById("input-rtmp-url") as HTMLInputElement;
  rtmpPortInput = document.getElementById(
    "input-rtmp-port",
  ) as HTMLInputElement;
  rtmpAppInput = document.getElementById("input-rtmp-app") as HTMLInputElement;
  rtmpKeyInput = document.getElementById("input-rtmp-key") as HTMLInputElement;
  btnCopyRtmp = document.getElementById("btn-copy-rtmp") as HTMLButtonElement;

  fileSelectInput = document.getElementById(
    "input-file-select",
  ) as HTMLInputElement;
  fileSelectBtn = document.getElementById(
    "btn-file-select",
  ) as HTMLButtonElement;

  inputFileChk = document.getElementById(
    "input-file-chunk",
  ) as HTMLInputElement;
  inputRtmpChk = document.getElementById(
    "input-rtmp-chunk",
  ) as HTMLInputElement;

  setupEventListeners();
  // Estado inicial basado en el signal actual
  updateInputSettingsUI(inputType.value);
}

function setupEventListeners(): void {
  // 1. Cambio de tipo de entrada
  if (inputTypeSelect) {
    inputTypeSelect.addEventListener("change", (e) => {
      const newType = (e.target as HTMLSelectElement).value;
      inputType.value = newType as "srt" | "rtmp" | "file";
    });
  }

  // 2. Actualización de URL de RTMP dinámica
  function handleRtmpChange() {
    calculateRtmpUrl();
  }

  [rtmpPortInput, rtmpAppInput, rtmpKeyInput].forEach((el) => {
    el?.addEventListener("input", handleRtmpChange);
    el?.addEventListener("change", handleRtmpChange);
  });

  // 3. Copiar URL RTMP
  if (btnCopyRtmp) {
    btnCopyRtmp.addEventListener("click", () => {
      if (rtmpUrlInput?.value && navigator.clipboard) {
        navigator.clipboard.writeText(rtmpUrlInput.value).then(() => {
          // Podríamos usar un toast aquí en el futuro
          btnCopyRtmp!.textContent = "✓";
          setTimeout(() => (btnCopyRtmp!.textContent = "📋"), 1000);
        });
      }
    });
  }

  // 4. Selección de archivo local
  if (fileSelectBtn && fileSelectInput) {
    fileSelectBtn.addEventListener("click", () => fileSelectInput?.click());
    fileSelectInput.addEventListener("change", (e) => {
      const target = e.target as HTMLInputElement;
      if (target.files && target.files.length > 0) {
        // Extraer path para entornos Electron/NW.js, o usar name en web nativo
        const path = target.value || target.files[0].name;
        // Aquí actualizaríamos un signal si existiera, o un estado global
        // Por ahora, actualizamos el input visualmente
        const pathInput = document.getElementById(
          "input-file-path",
        ) as HTMLInputElement;
        if (pathInput) pathInput.value = path;
      }
    });
  }
}

/**
 * Efecto reactivo: Muestra/oculta settings según `inputType`
 */
effect(() => {
  const currentType = inputType.value;
  updateInputSettingsUI(currentType);
});

function updateInputSettingsUI(type: string): void {
  if (srtSettings) srtSettings.style.display = type === "srt" ? "flex" : "none";
  if (rtmpSettings)
    rtmpSettings.style.display = type === "rtmp" ? "flex" : "none";
  if (fileSettings)
    fileSettings.style.display = type === "file" ? "flex" : "none";

  // Actualizar título del card
  const titleEl = document.getElementById("input-process-title");
  const titles: Record<string, string> = {
    srt: "📥 INPUT (SRT)",
    rtmp: "📥 INPUT (RTMP)",
    file: "📥 INPUT (Archivo)",
  };
  if (titleEl) titleEl.textContent = titles[type] || "📥 INPUT";

  // Si es RTMP, recalcular URL
  if (type === "rtmp") {
    calculateRtmpUrl();
  }
}

/**
 * Calcula la URL de RTMP a partir de los campos y actualiza el input.
 */
function calculateRtmpUrl(): void {
  if (!rtmpUrlInput || !rtmpPortInput || !rtmpAppInput || !rtmpKeyInput) return;

  const port = rtmpPortInput.value || "1935";
  const app = rtmpAppInput.value || "live";
  const key = rtmpKeyInput.value || "stream";

  rtmpUrlInput.value = `rtmp://127.0.0.1:${port}/${app}/${key}`;
}
