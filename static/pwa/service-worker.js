/* This worker deliberately never stores authenticated pages or financial data. */
const CACHE_NAME = 'pocketledger-public-__CACHE_VERSION__';
const PUBLIC_ASSETS = __PUBLIC_ASSETS__;
const OFFLINE_URL = __OFFLINE_URL__;

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(PUBLIC_ASSETS.map((url) => new Request(url, {
      credentials: 'omit', cache: 'reload',
    })));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => key.startsWith('pocketledger-public-') && key !== CACHE_NAME)
      .map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Each navigation is fetched afresh, including login/logout and user switches.
  // The fallback contains no account information. Successful HTML is never cached.
  if (request.mode === 'navigate') {
    event.respondWith(fetch(new Request(request, {cache: 'no-store'})).catch(async () => {
      const cache = await caches.open(CACHE_NAME);
      return await cache.match(OFFLINE_URL) || new Response('PocketLedger is offline. Reconnect and try again.', {
        status: 503, headers: {'Content-Type': 'text/plain; charset=utf-8'},
      });
    }));
    return;
  }

  // An exact allowlist, rather than a /static/ prefix, prevents future uploads or
  // personalized assets from entering this public cache. Queries bypass it too.
  if (url.search || !PUBLIC_ASSETS.includes(url.pathname)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(url.pathname);
    if (cached) return cached;
    const response = await fetch(new Request(request, {credentials: 'omit'}));
    if (response.ok && !response.redirected && response.type !== 'opaque') {
      await cache.put(url.pathname, response.clone());
    }
    return response;
  })());
});
