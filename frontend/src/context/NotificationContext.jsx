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

  const enableNotifications = useCallback(async () => {
    if (!isSupported) {
      throw new Error('Push notifications not supported');
    }

    setLoading(true);
    try {
      const subscriptionData = await subscribeToPush();
      setPermission(getPermissionState());

      // Send subscription to backend
      if (isAuthenticated) {
        await api.subscribePush(subscriptionData);
      }

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

      // Unsubscribe from backend for this device
      if (isAuthenticated) {
        await api.unsubscribePush(endpoint);
      }

      // Unsubscribe from browser
      await unsubscribeFromPush();
      await syncNotificationState();
      return true;
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, syncNotificationState]);

  const value = {
    isSupported,
    permission,
    isSubscribed,
    loading,
    enableNotifications,
    disableNotifications,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}
