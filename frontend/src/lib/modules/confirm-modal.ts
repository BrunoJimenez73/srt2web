/**
 * Confirmation Modal Module for SRT2Web
 *
 * Replaces native browser confirm() with a custom modal
 * Usage: const confirmed = await showConfirm('¿Está seguro?');
 */

// ── State ────────────────────────────────────────────────────────

let modalElement: HTMLElement | null = null;
let resolvePromise: ((value: boolean) => void) | null = null;

// ── Create Modal DOM ─────────────────────────────────────────────

function createModal(): HTMLElement {
  const modal = document.createElement("div");
  modal.id = "confirm-modal";
  modal.className = "confirm-modal-overlay hidden";
  modal.setAttribute("role", "dialog");
  modal.setAttribute("aria-modal", "true");
  modal.setAttribute("aria-labelledby", "confirm-title");
  modal.setAttribute("aria-describedby", "confirm-message");

  modal.innerHTML = `
    <div class="confirm-modal-content" role="document">
      <h3 id="confirm-title" class="confirm-title">Confirmación</h3>
      <p id="confirm-message" class="confirm-message"></p>
      <div class="confirm-buttons">
        <button id="btn-confirm-cancel" class="btn btn-ghost" aria-label="Cancelar">
          Cancelar
        </button>
        <button id="btn-confirm-ok" class="btn btn-error" aria-label="Confirmar">
          Confirmar
        </button>
      </div>
    </div>
  `;

  // Add styles if not already present
  if (!document.getElementById("confirm-modal-styles")) {
    const style = document.createElement("style");
    style.id = "confirm-modal-styles";
    style.textContent = `
      .confirm-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.3s ease;
      }

      .confirm-modal-overlay.visible {
        opacity: 1;
      }

      .confirm-modal-content {
        background: var(--color-card, #1a1a24);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 24px;
        max-width: 400px;
        width: 90%;
        transform: scale(0.9);
        transition: transform 0.3s ease;
      }

      .confirm-modal-overlay.visible .confirm-modal-content {
        transform: scale(1);
      }

      .confirm-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--color-surface-light, #e4e4e8);
        margin-bottom: 8px;
      }

      .confirm-message {
        font-size: 13px;
        color: var(--color-surface-dim, #8888a0);
        margin-bottom: 20px;
        line-height: 1.5;
      }

      .confirm-buttons {
        display: flex;
        gap: 8px;
        justify-content: flex-end;
      }
    `;
    document.head.appendChild(style);
  }

  // Add event listeners
  modal.querySelector("#btn-confirm-cancel")?.addEventListener("click", () => {
    closeModal(false);
  });

  modal.querySelector("#btn-confirm-ok")?.addEventListener("click", () => {
    closeModal(true);
  });

  // Close on overlay click
  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      closeModal(false);
    }
  });

  // Close on Escape key
  modal.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeModal(false);
    }
  });

  return modal;
}

// ── Modal Control ───────────────────────────────────────────────────

function openModal(message: string): void {
  if (!modalElement) {
    modalElement = createModal();
    document.body.appendChild(modalElement);
  }

  const messageEl = modalElement.querySelector("#confirm-message");
  if (messageEl) messageEl.textContent = message;

  // Show modal
  modalElement.classList.remove("hidden");
  requestAnimationFrame(() => {
    modalElement?.classList.add("visible");
  });

  // Focus the cancel button
  setTimeout(() => {
    (
      modalElement?.querySelector("#btn-confirm-cancel") as HTMLElement | null
    )?.focus();
  }, 100);
}

function closeModal(confirmed: boolean): void {
  if (!modalElement) return;

  modalElement.classList.remove("visible");

  setTimeout(() => {
    modalElement?.classList.add("hidden");
    if (resolvePromise) {
      resolvePromise(confirmed);
      resolvePromise = null;
    }
  }, 300);
}

// ── Public API ─────────────────────────────────────────────────────

/**
 * Show a confirmation modal
 * @param message - The message to display
 * @returns Promise<boolean> - true if confirmed, false if cancelled
 */
export async function showConfirm(message: string): Promise<boolean> {
  return new Promise((resolve) => {
    resolvePromise = resolve;
    openModal(message);
  });
}

/**
 * Show a delete confirmation (convenience wrapper)
 * @param itemName - Name of the item to delete
 * @returns Promise<boolean>
 */
export async function showDeleteConfirm(itemName: string): Promise<boolean> {
  return showConfirm(`¿Eliminar "${itemName}"?`);
}

export default {
  showConfirm,
  showDeleteConfirm,
};
