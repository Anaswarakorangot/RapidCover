// RapidCover Service Worker
// Handles caching and push notifications

const CACHE_NAME = 'rapidcover-v2';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/icon-192.png',
  '/icon-512.png',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch event - network first for API, cache first for assets
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;

  // In local dev, avoid serving cached Vite assets
  if (self.location.hostname === 'localhost' && self.location.port === '5173') {
    event.respondWith(fetch(request));
    return;
  }

  // API requests: network first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Static assets: cache first
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        fetch(request).then((response) => {
          if (response.ok) {
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, response);
            });
          }
        });
        return cached;
      }
      return fetch(request).then((response) => {
        if (response.ok) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return response;
      });
    })
  );
});

// Push notification event
self.addEventListener('push', (event) => {
  if (!event.data) {
    console.log('Push event with no data');
    return;
  }

  let data;
  try {
    data = event.data.json();
  } catch (e) {
    data = {
      title: 'RapidCover',
      body: event.data.text(),
      icon: '/icon-192.png',
    };
  }

  const options = {
    body: data.body || '',
    icon: data.icon || '/icon-192.png',
    badge: '/icon-192.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/',
      claim_id: data.claim_id,
      type: data.type,
    },
    tag: data.tag || 'rapidcover-notification',
    renotify: true,
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'RapidCover', options)
  );
});

// Notification click event - correct routing based on notification type
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const notificationData = event.notification.data || {};
  const notificationType = notificationData.type;
  const claimId = notificationData.claim_id;

  // Determine the correct route based on notification type
  const ROUTE_MAP = {
    claim_created: '/claims',
    claim_approved: '/claims',
    claim_paid: '/claims',
    claim_rejected: '/claims',
    trigger_alert: '/',
  };

  const targetRoute = ROUTE_MAP[notificationType] || notificationData.url || '/';
  const targetUrl = self.location.origin + targetRoute;

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Try to find an existing open window and navigate it
      for (const client of clientList) {
        if (client.url.startsWith(self.location.origin) && 'focus' in client) {
          // Post message to app for in-app navigation (React Router)
          client.postMessage({
            type: 'NOTIFICATION_CLICK',
            notificationType,
            claimId,
            url: targetRoute,
          });
          return client.focus();
        }
      }
      // No window open - open a new one
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});