// Cache only the public offline notice. Never store API, sessions or financial data.
const CACHE = 'pocketledger-flutter-public-v1';
const OFFLINE = new URL('offline.html', self.registration.scope).href;
const SCOPE_PATH = new URL(self.registration.scope).pathname;
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.add(OFFLINE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('pocketledger-flutter-public-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || !url.pathname.startsWith(SCOPE_PATH)) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(async () => {
      try {
        const notice = await caches.match(OFFLINE, {cacheName: CACHE});
        if (notice) return notice;
      } catch (_) {
        // Storage may be unavailable or evicted; still return a useful page.
      }
      return new Response('PocketLedger is offline. Reconnect to your server and reload. Changes are not queued offline.', {
        status: 503,
        headers: {'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store'},
      });
    }));
  }
});
