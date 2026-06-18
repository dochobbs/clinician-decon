const CACHE_NAME = "decon-static-v5";
const OLD_CACHES = ["decon-static-v1", "decon-static-v2", "decon-static-v3", "decon-static-v4"];
const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/styles.css",
  "/app.js",
  "/manifest.json",
  "/favicon.ico",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(
        names
          .filter((name) => name !== CACHE_NAME || OLD_CACHES.includes(name))
          .map((name) => caches.delete(name))
      ))
      .then(() => clients.claim())
      .then(() => clients.matchAll({ type: "window", includeUncontrolled: true }))
      .then((clientList) => Promise.all(
        clientList.map((client) => {
          const url = new URL(client.url);
          return url.origin === self.location.origin ? client.navigate(client.url) : undefined;
        })
      ))
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || event.request.url.includes("/api/")) return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
