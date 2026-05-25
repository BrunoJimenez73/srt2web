let deferredPrompt: BeforeInstallPromptEvent | null = null;

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
  prompt(): Promise<void>;
}

declare global {
  interface WindowEventMap {
    beforeinstallprompt: BeforeInstallPromptEvent;
    appinstalled: Event;
  }
}

export function registerSW(): void {
  if (!("serviceWorker" in navigator)) return;

  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/service-worker.js")
      .then(() => {
        if (import.meta.env.DEV) console.info("PWA: Service worker registered");
      })
      .catch((err) => {
        console.warn("PWA: Service worker registration failed", err);
      });
  });
}

export function getDeferredPrompt(): BeforeInstallPromptEvent | null {
  return deferredPrompt;
}

export function clearDeferredPrompt(): void {
  deferredPrompt = null;
}

export function initPWA(): void {
  registerSW();

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
  });

  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
  });
}

export function isInstallable(): boolean {
  return deferredPrompt !== null;
}

export async function triggerInstall(): Promise<boolean> {
  if (!deferredPrompt) return false;

  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  deferredPrompt = null;

  return outcome === "accepted";
}
