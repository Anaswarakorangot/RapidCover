/* global clients */
// RapidCover Service Worker

const CACHE_NAME = 'rapidcover-v3';
const STATIC_ASSETS = ['/', '/index.html', '/favicon.svg', '/manifest.json'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .catch(err => console.log('[SW] Pre-cache failed (some assets might be missing):', err))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(names =>
      Promise.all(names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== 'GET') return;

  // Skip chrome-extension and other non-http(s) schemes
  if (!url.protocol.startsWith('http')) return;

  // During development, don't intercept API calls to avoid CORS/Cache issues
  if (url.port === '8000' || url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request));
    return;
  }

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(c => c.put(request, clone));
        }
        return res;
      }).catch(() => caches.match(request))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(cached => {
      if (cached) {
        fetch(request).then(res => {
          if (res.ok) caches.open(CACHE_NAME).then(c => c.put(request, res));
        });
        return cached;
      }
      return fetch(request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(c => c.put(request, clone));
        }
        return res;
      });
    })
  );
});

// Push event
self.addEventListener('push', (event) => {
  if (!event.data) return;
  let data;
  try { data = event.data.json(); }
  catch { data = { title: 'RapidCover', body: event.data.text(), icon: '/icon-192.png' }; }

  event.waitUntil(
    self.registration.showNotification(data.title || 'RapidCover', {
      body: data.body || '',
      icon: data.icon || '/icon-192.png',
      badge: '/icon-192.png',
      vibrate: [100, 50, 100],
      data: { url: data.url || '/', claim_id: data.claim_id, type: data.type },
      tag: data.tag || 'rapidcover-notification',
      renotify: true,
    })
  );
});

// Notification click — route correctly based on type, message open app window
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const ROUTE_MAP = {
    claim_created: '/claims',
    claim_approved: '/claims',
    claim_paid: '/claims',
    claim_rejected: '/claims',
    trigger_alert: '/',
  };

  const notifData = event.notification.data || {};
  const notificationType = notifData.type;
  const targetRoute = ROUTE_MAP[notificationType] || notifData.url || '/';
  const targetUrl = self.location.origin + targetRoute;

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      for (const client of clientList) {
        if (client.url.startsWith(self.location.origin) && 'focus' in client) {
          // Tell the React app to navigate via React Router
          client.postMessage({ type: 'NOTIFICATION_CLICK', notificationType, url: targetRoute });
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(targetUrl);
    })
  );
});