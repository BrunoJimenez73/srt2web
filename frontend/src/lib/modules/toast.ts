/**
 * Módulo para el sistema de notificaciones Toast
 * Maneja la creación y eliminación de notificaciones
 */

export type ToastType = "success" | "error" | "info";

/**
 * Muestra una notificación toast
 * @param message - El mensaje a mostrar
 * @param type - El tipo de toast (success, error, info)
 * @param duration - Duración en milisegundos (default: 3000)
 */
export function showToast(
  message: string,
  type: ToastType = "info",
  duration: number = 3000,
): void {
  const container = document.getElementById("toast-container");
  if (!container) {
    console.error("Toast container not found");
    return;
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  toast.setAttribute("role", "status");
  toast.setAttribute("aria-live", "polite");

  container.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.add("toast-show");
  });

  // Auto remove
  setTimeout(() => {
    toast.classList.remove("toast-show");
    // Remove from DOM after animation
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, duration);
}

/**
 * Limpia todos los toasts activos
 */
export function clearAllToasts(): void {
  const container = document.getElementById("toast-container");
  if (container) {
    container.innerHTML = "";
  }
}
