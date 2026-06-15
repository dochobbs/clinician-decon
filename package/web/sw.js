self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open("decon-static-v1").then((cache) => cache.addAll([
      "/",
      "/index.html",
      "/styles.css",
      "/app.js",
      "/manifest.json"
    ]))
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.url.includes("/api/")) return;
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
