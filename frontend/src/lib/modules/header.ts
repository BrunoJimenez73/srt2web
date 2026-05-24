/**
 * Módulo para la lógica del Header
 * Maneja el panel de seguridad, token de autenticación y estado del WebSocket
 */

import { getAuthToken, setAuthToken } from "../api";
import { showToast } from "./toast";

// DOM Elements
let btnToggle: HTMLButtonElement | null = null;
let panel: HTMLDivElement | null = null;
let arrow: HTMLSpanElement | null = null;
let label: HTMLSpanElement | null = null;
let tokenInput: HTMLInputElement | null = null;
let btnEye: HTMLButtonElement | null = null;
let btnGen: HTMLButtonElement | null = null;
let btnSave: HTMLButtonElement | null = null;
let btnClose: HTMLButtonElement | null = null;

/**
 * Actualiza el estado visual del botón de seguridad según el token guardado
 */
export function updateSecureState(): void {
  const token = getAuthToken();
  if (token) {
    if (label) label.textContent = "Secure ON";
    btnToggle?.classList.add("active");
    if (tokenInput) tokenInput.value = token;
  } else {
    if (label) label.textContent = "Secure OFF";
    btnToggle?.classList.remove("active");
    if (tokenInput) tokenInput.value = "";
  }
}

/**
 * Alterna la visibilidad del panel de seguridad
 */
function togglePanel(): void {
  if (!panel || !arrow) return;

  const isHidden = panel.classList.toggle("hidden");
  arrow.classList.toggle("open", !isHidden);

  if (!isHidden) {
    updateSecureState();
    tokenInput?.focus();
  }
}

/**
 * Cierra el panel de seguridad
 */
function closePanel(): void {
  if (!panel || !arrow) return;
  panel.classList.add("hidden");
  arrow.classList.remove("open");
}

/**
 * Alterna la visibilidad del token (password/text)
 */
function toggleTokenVisibility(): void {
  if (!tokenInput || !btnEye) return;

  if (tokenInput.type === "password") {
    tokenInput.type = "text";
    btnEye.textContent = "🙈";
  } else {
    tokenInput.type = "password";
    btnEye.textContent = "👁";
  }
}

/**
 * Genera un token aleatorio seguro
 */
function generateToken(): void {
  if (!tokenInput || !btnEye) return;

  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  const length = 32;
  let token = "";
  const array = new Uint32Array(length);
  crypto.getRandomValues(array);

  for (let i = 0; i < length; i++) {
    token += chars[array[i] % chars.length];
  }

  tokenInput.value = token;
  tokenInput.type = "text";
  btnEye.textContent = "🙈";
}

/**
 * Guarda el token de autenticación
 */
function saveToken(): void {
  if (!tokenInput) return;

  const token = tokenInput.value.trim();
  setAuthToken(token);
  updateSecureState();

  const message = token
    ? "🔐 Token guardado. Recarga para aplicar."
    : "🔓 Autenticación desactivada.";
  const type = token ? "success" : "info";

  showToast(message, type);
  closePanel();
}

/**
 * Maneja clicks fuera del panel para cerrarlo
 */
function handleOutsideClick(e: Event): void {
  if (!panel || !btnToggle) return;

  const target = e.target as Node;
  if (!panel.contains(target) && !btnToggle.contains(target)) {
    closePanel();
  }
}

/**
 * Inicializa el panel de seguridad del header
 */
export function initSecurityPanel(): void {
  // Get DOM elements
  btnToggle = document.getElementById("btn-secure-toggle") as HTMLButtonElement;
  panel = document.getElementById("secure-panel") as HTMLDivElement;
  arrow = document.getElementById("secure-arrow") as HTMLSpanElement;
  label = document.getElementById("secure-label") as HTMLSpanElement;
  tokenInput = document.getElementById(
    "secure-token-input",
  ) as HTMLInputElement;
  btnEye = document.getElementById("btn-eye-token") as HTMLButtonElement;
  btnGen = document.getElementById("btn-gen-token") as HTMLButtonElement;
  btnSave = document.getElementById("btn-save-secure") as HTMLButtonElement;
  btnClose = document.getElementById("btn-close-secure") as HTMLButtonElement;

  // Setup event listeners
  btnToggle?.addEventListener("click", (e: Event) => {
    e.stopPropagation();
    togglePanel();
  });

  btnClose?.addEventListener("click", closePanel);

  document.addEventListener("click", handleOutsideClick);

  btnEye?.addEventListener("click", toggleTokenVisibility);

  btnGen?.addEventListener("click", generateToken);

  btnSave?.addEventListener("click", saveToken);

  // Initialize state
  updateSecureState();
}

/**
 * Limpia los event listeners (para cleanup)
 */
export function cleanupSecurityPanel(): void {
  document.removeEventListener("click", handleOutsideClick);
}
