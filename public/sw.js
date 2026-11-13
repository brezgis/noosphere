// AUTO_VERSION is replaced by build.sh on each deploy
const CACHE_NAME = 'noosphere-AUTO_VERSION';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/style.css',
  '/app.js',
  '/garden.js',
  '/favicon.svg',
  '/favicon.png',
  '/icon-192.png',
  '/icon-512.png',
  '/manifest.json',
];

// Install: cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: the network wins whenever it answers, and the cache covers offline.
// (Cache-first used to pin an old page until the service worker itself was
// replaced, which made a redesign arrive a visit late.)
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;

  event.respondWith(
    fetch(event.request)
      .then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return resp;
      })
      .catch(() => caches.match(event.request, { ignoreSearch: url.pathname.startsWith('/api/') }))
  );
});
