import { useState } from 'react';
import { useNotifications } from '../hooks/useNotifications';

export function NotificationToggle() {
  const {
    isSupported,
    permission,
    isSubscribed,
    loading,
    enableNotifications,
    disableNotifications,
  } = useNotifications();
  const [error, setError] = useState(null);

  if (!isSupported) {
    return (
      <div className="flex items-center justify-between py-3 border-b border-gray-100">
        <div>
          <p className="text-gray-700">Push Notifications</p>
          <p className="text-xs text-gray-400">Not supported on this device</p>
        </div>
        <span className="text-gray-400 text-sm">Unavailable</span>
      </div>
    );
  }

  if (permission === 'denied') {
    return (
      <div className="flex items-center justify-between py-3 border-b border-gray-100">
        <div>
          <p className="text-gray-700">Push Notifications</p>
          <p className="text-xs text-gray-400">Blocked in browser settings</p>
        </div>
        <span className="text-red-500 text-sm">Blocked</span>
      </div>
    );
  }

  async function handleToggle() {
    setError(null);
    try {
      if (isSubscribed) {
        await disableNotifications();
      } else {
        await enableNotifications();
      }
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="py-3 border-b border-gray-100">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-700">Push Notifications</p>
          <p className="text-xs text-gray-400">
            {isSubscribed ? 'Receive claim alerts' : 'Get notified about claims'}
          </p>
        </div>
        <button
          onClick={handleToggle}
          disabled={loading}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            isSubscribed ? 'bg-blue-600' : 'bg-gray-200'
          } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              isSubscribed ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}
