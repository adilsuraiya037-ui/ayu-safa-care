const CACHE_NAME = "ayu-safa-static-v1";
const APP_SHELL = [
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png"
];

// Cache only app icons. Do not cache product pages, checkout, tracking, admin,
// customer information, or order requests.
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  // Never intercept private or transactional pages.
  if (
    url.pathname.startsWith("/admin") ||
    url.pathname.startsWith("/place-order") ||
    url.pathname.startsWith("/track-order") ||
    url.pathname.startsWith("/checkout") ||
    url.pathname.startsWith("/login")
  ) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => new Response(
        "<!doctype html><html lang='en'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Offline</title><body style='font-family:Arial;background:#07140d;color:white;padding:2rem'><h1>AYU SAFA CARE</h1><p>You are offline. Reconnect to browse products, place orders, track orders, or use the admin panel.</p></body></html>",
        { headers: { "Content-Type": "text/html; charset=utf-8" } }
      ))
    );
  }
});
