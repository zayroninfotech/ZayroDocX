const CACHE = 'zayrodesk-v1';
const OFFLINE_URL = '/tools/zayrodesk/';

// Assets to pre-cache
const PRECACHE = [
  '/tools/zayrodesk/',
  'https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js',
  'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(PRECACHE).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // Only handle GET requests
  if (e.request.method !== 'GET') return;
  // Skip API calls — always go to network
  if (e.request.url.includes('/api/desk/')) return;

  e.respondWith(
    fetch(e.request)
      .then(res => {
        // Cache successful page responses
        if (res.ok && e.request.url.includes('/tools/zayrodesk/')) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request).then(r => r || caches.match(OFFLINE_URL)))
  );
});
