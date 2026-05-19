function r() {
  "serviceWorker" in navigator &&
    window.addEventListener("load", () => {
      navigator.serviceWorker
        .register("/service-worker.js")
        .then(() => {
          console.info("PWA: Service worker registered");
        })
        .catch((e) => {
          console.warn("PWA: Service worker registration failed", e);
        });
    });
}
function i() {
  r(),
    window.addEventListener("beforeinstallprompt", (e) => {
      e.preventDefault();
    }),
    window.addEventListener("appinstalled", () => {});
}
export { i as initPWA, r as registerSW };
