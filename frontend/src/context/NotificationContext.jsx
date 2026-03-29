import { createContext, useContext, useState, useEffect, useCallback } from 'react';
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

const NotificationContext = createContext(null);

export function NotificationProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [isSupported, setIsSupported] = useState(false);
  const [permission, setPermission] = useState('default');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [loading, setLoading] = useState(true);

  // Register service worker and check state on mount
  useEffect(() => {
    const init = async () => {
      const supported = isPushSupported();
      setIsSupported(supported);

      if (supported) {
        // Register service worker
        try {
          await registerServiceWorker();
        } catch (err) {
          console.warn('Service worker registration failed:', err);
        }

        setPermission(getPermissionState());

        try {
          const subscription = await getCurrentSubscription();
          setIsSubscribed(!!subscription);
        } catch {
          setIsSubscribed(false);
        }
      }

      setLoading(false);
    };

    init();
  }, []);

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

      setIsSubscribed(true);
      return true;
    } catch (error) {
      setPermission(getPermissionState());
      throw error;
    } finally {
      setLoading(false);
    }
  }, [isSupported, isAuthenticated]);

  const disableNotifications = useCallback(async () => {
    setLoading(true);
    try {
      // Unsubscribe from browser
      await unsubscribeFromPush();

      // Unsubscribe from backend
      if (isAuthenticated) {
        await api.unsubscribePush();
      }

      setIsSubscribed(false);
      return true;
    } catch (error) {
      throw error;
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

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

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}
