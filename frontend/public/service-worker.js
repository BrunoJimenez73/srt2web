// Bump CACHE_NAME on every breaking change to evict old client caches.
// IMPORTANT: live content (HLS, subtitles, API, WebSocket upgrade) must NEVER be cached,
// otherwise the player will replay stale segments from a previous session.
const CACHE_NAME = "srt2web-v3";

// Only truly static, fingerprintable assets belong in the precache.
const ASSETS_TO_CACHE = [
  "/manifest.json",
  "/favicon.svg",
  "/favicon.ico",
  "/icons/icon-192.svg",
  "/icons/icon-512.svg",
];

// Any request whose URL path starts with one of these prefixes is treated as
// "live" and is always fetched from the network, with no cache reads/writes.
const NO_CACHE_PATH_PREFIXES = [
  "/hls/",
  "/subtitles/",
  "/recordings/",
  "/api/",
  "/ws",
  "/health",
  "/ready",
  "/live",
  "/player",
  "/webrtc-player",
];

function isNoCachePath(url) {
  const path = url.pathname;
  for (const prefix of NO_CACHE_PATH_PREFIXES) {
    if (path === prefix || path.startsWith(prefix)) return true;
  }
  return false;
}

function isHashedStaticAsset(url) {
  // Astro fingerprints assets under /_astro/ — these are safe to cache long-term.
  return url.pathname.startsWith("/_astro/");
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE)),
  );
  // Activate this worker as soon as possible so the stale cache is replaced.
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key)),
      );
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("message", (event) => {
  // Allow the app to force a cache purge (e.g. when starting a new pipeline session).
  if (event.data && event.data.type === "CLEAR_CACHES") {
    event.waitUntil(
      (async () => {
        const keys = await caches.keys();
        await Promise.all(keys.map((key) => caches.delete(key)));
      })(),
    );
  }
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  // Only handle same-origin requests; let the browser deal with the rest.
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Live content: ALWAYS go to the network, never read or write the cache.
  // .catch() is critical: without it, a transient server error causes the
  // promise to reject, the browser gets a opaque network error, and the UI
  // shows "Failed to fetch" for everything (outputs, subtitles, pipeline stop).
  if (isNoCachePath(url)) {
    event.respondWith(
      fetch(request, { cache: "no-store" }).catch(() => {
        return new Response("Service unavailable", {
          status: 503,
          statusText: "Service Unavailable",
        });
      }),
    );
    return;
  }

  // Hashed Astro bundles: cache-first (safe — filename changes on update).
  if (isHashedStaticAsset(url)) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
      }),
    );
    return;
  }

  // Everything else (HTML shell, manifest, icons): network-first with cache fallback.
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(() => {
        return caches
          .match(request)
          .then((cached) => cached || new Response("Offline", { status: 503 }));
      }),
  );
});
