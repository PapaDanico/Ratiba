/*
 * Ratiba service worker — deliberately conservative.
 *
 * - Navigations are NETWORK-FIRST, so a new deploy is always picked up
 *   when online (no stale-app-shell footgun); the cached shell is only a
 *   fallback when offline.
 * - Vite content-hashes /assets/* filenames, so those are immutable and
 *   safe to serve cache-first.
 * - /api/* and non-GET requests are never intercepted.
 */
const CACHE = "ratiba-cache-v2";

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches
      .open(CACHE)
      .then((c) => c.add("/"))
      .catch(() => {}),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // third-party (fonts, etc.)
  if (url.pathname.startsWith("/api")) return; // never touch the API

  // HTML navigations: network-first, fall back to cached shell offline.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches
            .open(CACHE)
            .then((c) => c.put("/", copy))
            .catch(() => {});
          return res;
        })
        .catch(() => caches.match("/").then((hit) => hit || Response.error())),
    );
    return;
  }

  // Immutable hashed build assets: cache-first.
  if (url.pathname.startsWith("/assets/")) {
    event.respondWith(
      caches.match(req).then(
        (hit) =>
          hit ||
          fetch(req).then((res) => {
            const copy = res.clone();
            caches
              .open(CACHE)
              .then((c) => c.put(req, copy))
              .catch(() => {});
            return res;
          }),
      ),
    );
    return;
  }

  // Everything else: try the network, fall back to cache if offline.
  event.respondWith(fetch(req).catch(() => caches.match(req)));
});
