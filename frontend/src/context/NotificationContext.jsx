import { useState, useEffect, useCallback } from 'react';
import {
  isPushSupported,
  getPermissionState,
  subscribeToPush,
  unsubscribeFromPush,
  getCurrentSubscription,
  registerServiceWorker,
} from '../services/pushNotifications';
import api from '../services/api';
import { useAuth } from './AuthContext';
import { NotificationContext } from './NotificationContextValue';

// Map notification types → correct frontend routes
const NOTIFICATION_ROUTES = {
  claim_created: '/claims',
  claim_approved: '/claims',
  claim_paid: '/claims',
  claim_rejected: '/claims',
  trigger_alert: '/',
};

export function NotificationProvider({ children }) {
  const { isAuthenticated, user } = useAuth();
  const [isSupported, setIsSupported] = useState(false);
  const [permission, setPermission] = useState('default');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [loading, setLoading] = useState(true);

  const syncNotificationState = useCallback(async () => {
    const supported = isPushSupported();
    setIsSupported(supported);
    setPermission(supported ? getPermissionState() : 'unsupported');

    if (!supported) {
      setIsSubscribed(false);
      return;
    }

    try {
      await registerServiceWorker();
    } catch (err) {
      console.warn('Service worker registration failed:', err);
    }

    let endpoint = null;
    try {
      const subscription = await getCurrentSubscription();
      endpoint = subscription?.endpoint || null;
    } catch {
      endpoint = null;
    }

    if (!isAuthenticated) {
      setIsSubscribed(false);
      return;
    }

    try {
      const status = await api.getNotificationStatus(endpoint);
      setIsSubscribed(status.is_subscribed);
    } catch {
      setIsSubscribed(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      try {
        await syncNotificationState();
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [syncNotificationState, user?.id]);

  // Listen for SW messages → navigate to the correct route on notification click
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return;

    const handleMessage = (event) => {
      if (event.data?.type === 'NOTIFICATION_CLICK') {
        const { notificationType, url } = event.data;
        const route = NOTIFICATION_ROUTES[notificationType] || url || '/';
        window.location.href = route;
      }
    };

    navigator.serviceWorker.addEventListener('message', handleMessage);
    return () => navigator.serviceWorker.removeEventListener('message', handleMessage);
  }, []);

  const enableNotifications = useCallback(async () => {
    if (!isSupported) throw new Error('Push notifications not supported');

    setLoading(true);
    try {
      const subscriptionData = await subscribeToPush();
      setPermission(getPermissionState());
      if (isAuthenticated) await api.subscribePush(subscriptionData);
      await syncNotificationState();
      return true;
    } catch (error) {
      setPermission(getPermissionState());
      throw error;
    } finally {
      setLoading(false);
    }
  }, [isSupported, isAuthenticated, syncNotificationState]);

  const disableNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const currentSubscription = await getCurrentSubscription();
      const endpoint = currentSubscription?.endpoint || null;
      if (isAuthenticated) await api.unsubscribePush(endpoint);
      await unsubscribeFromPush();
      await syncNotificationState();
      return true;
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, syncNotificationState]);

  const value = { isSupported, permission, isSubscribed, loading, enableNotifications, disableNotifications };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}
