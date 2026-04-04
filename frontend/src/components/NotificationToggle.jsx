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
      <div className="notif-toggle-row" style={{ opacity: 0.6 }}>
        <div>
          <p style={{ fontWeight: 700, color: 'var(--text-dark)' }}>Push Notifications</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-light)' }}>Not supported on this device</p>
        </div>
        <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-mid)' }}>UNAVAILABLE</span>
      </div>
    );
  }

  if (permission === 'denied') {
    return (
      <div className="notif-toggle-row">
        <div>
          <p style={{ fontWeight: 700, color: 'var(--text-dark)' }}>Push Notifications</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--error)' }}>Blocked in browser settings</p>
        </div>
        <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--error)' }}>BLOCKED</span>
      </div>
    );
  }

  async function handleToggle() {
    setError(null);
    try {
      if (isSubscribed) {
        // Optimistic UI could be tricky with permissions, 
        // but we'll focus on making the backend call feel fast.
        await disableNotifications();
      } else {
        await enableNotifications();
      }
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="notif-toggle-container">
      <div className="notif-toggle-row" onClick={!loading ? handleToggle : undefined} style={{ cursor: loading ? 'wait' : 'pointer' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '1.25rem' }}>🔔</span>
          <div>
            <p style={{ fontWeight: 800, fontSize: '1rem', color: 'var(--text-dark)', fontFamily: 'Nunito' }}>Push Notifications</p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-mid)', fontWeight: 600 }}>
              {isSubscribed ? 'Receive claim alerts' : 'Get notified about claims'}
            </p>
          </div>
        </div>
        
        <div className={`premium-switch ${isSubscribed ? 'active' : ''} ${loading ? 'loading' : ''}`}>
          <div className="premium-switch-handle" />
        </div>
      </div>
      {error && <p style={{ color: 'var(--error)', fontSize: '0.7rem', marginTop: '8px', fontWeight: 600 }}>{error}</p>}

      <style dangerouslySetInnerHTML={{ __html: `
        .notif-toggle-container {
          padding: 1rem 0;
        }
        .notif-toggle-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.5rem 0;
          transition: all 0.2s ease;
        }
        .premium-switch {
          width: 48px;
          height: 26px;
          background: #e2e8f0;
          border-radius: 50px;
          position: relative;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          border: 2px solid transparent;
        }
        .premium-switch.active {
          background: #22c55e;
          box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
        }
        .premium-switch.loading {
          opacity: 0.6;
        }
        .premium-switch-handle {
          width: 20px;
          height: 20px;
          background: white;
          border-radius: 50%;
          position: absolute;
          top: 1px;
          left: 2px;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .premium-switch.active .premium-switch-handle {
          left: 22px;
        }
      `}} />
    </div>
  );
}
