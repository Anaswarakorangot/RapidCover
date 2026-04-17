import { useState, useEffect } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function DemoModeBanner() {
  const [demoMode, setDemoMode] = useState(false);

  const checkDemoMode = async () => {
    try {
      const res = await authenticatedFetch(`${API}/admin/panel/demo-mode/status`);
      if (res.ok) {
        const data = await res.json();
        setDemoMode(data.enabled || data.demo_mode); // Support both new and old format
      }
    } catch {
      // Silently fail
    }
  };

  useEffect(() => {
    checkDemoMode(); // eslint-disable-line react-hooks/set-state-in-effect
    // Check every 10 seconds
    const interval = setInterval(checkDemoMode, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!demoMode) return null;

  return (
    <div style={{
      background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
      color: 'white',
      padding: '0.75rem 1.5rem',
      textAlign: 'center',
      fontWeight: 700,
      fontSize: '0.9rem',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      position: 'sticky',
      top: 0,
      zIndex: 1000,
      animation: 'slideDown 0.3s ease'
    }}>
      <style>{`
        @keyframes slideDown {
          from { transform: translateY(-100%); }
          to { transform: translateY(0); }
        }
      `}</style>
      🎭 DEMO MODE ACTIVE - All data is simulated for demonstration purposes
    </div>
  );
}
