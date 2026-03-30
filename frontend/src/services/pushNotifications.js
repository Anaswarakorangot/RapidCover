const VAPID_PUBLIC_KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY;

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export function isPushSupported() {
  return (
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  );
}

export function getPermissionState() {
  if (!isPushSupported()) return 'unsupported';
  return Notification.permission;
}

export async function requestPermission() {
  if (!isPushSupported()) {
    throw new Error('Push notifications not supported');
  }
  const permission = await Notification.requestPermission();
  return permission;
}

export async function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) {
    throw new Error('Service workers not supported');
  }

  try {
    const registration = await navigator.serviceWorker.register('/sw.js', {
      scope: '/',
    });
    console.log('Service Worker registered:', registration.scope);
    return registration;
  } catch (error) {
    console.error('Service Worker registration failed:', error);
    throw error;
  }
}

export async function getServiceWorkerRegistration() {
  if (!('serviceWorker' in navigator)) {
    throw new Error('Service workers not supported');
  }

  // First try to get existing registration
  let registration = await navigator.serviceWorker.getRegistration();

  // If no registration, register the service worker
  if (!registration) {
    registration = await registerServiceWorker();
  }

  // Wait for the service worker to be ready
  await navigator.serviceWorker.ready;

  return registration;
}

export async function getCurrentSubscription() {
  const registration = await getServiceWorkerRegistration();
  return registration.pushManager.getSubscription();
}

export async function subscribeToPush() {
  if (!isPushSupported()) {
    throw new Error('Push notifications not supported');
  }

  if (!VAPID_PUBLIC_KEY) {
    throw new Error('VAPID public key not configured');
  }

  const permission = await requestPermission();
  if (permission !== 'granted') {
    throw new Error('Permission denied');
  }

  const registration = await getServiceWorkerRegistration();

  // Check for existing subscription
  let subscription = await registration.pushManager.getSubscription();

  if (!subscription) {
    // Create new subscription
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
    });
  }

  return subscriptionToJSON(subscription);
}

export async function unsubscribeFromPush() {
  const subscription = await getCurrentSubscription();
  if (subscription) {
    await subscription.unsubscribe();
    return true;
  }
  return false;
}

function subscriptionToJSON(subscription) {
  const json = subscription.toJSON();
  return {
    endpoint: json.endpoint,
    p256dh_key: json.keys.p256dh,
    auth_key: json.keys.auth,
  };
}
