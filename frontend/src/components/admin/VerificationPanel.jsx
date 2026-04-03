// frontend/src/components/admin/VerificationPanel.jsx
// System health verification panel with check results

import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const CHECK_ICONS = {
  database: '🗄️',
  auth_endpoint: '🔐',
  zone_list: '🗺️',
  trigger_engine: '⚙️',
  simulation: '🎭',
  claim_creation: '📋',
  payout_service: '💳',
  push_notifications: '🔔',
  data_sources: '📡',
};

const CHECK_DESCRIPTIONS = {
  database: 'Database connection healthy',
  auth_endpoint: 'Authentication service available',
  zone_list: 'Zone data accessible',
  trigger_engine: 'Trigger engine operational',
  simulation: 'Mock APIs injectable',
  claim_creation: 'Claims processor available',
  payout_service: 'Payout service configured',
  push_notifications: 'VAPID keys configured',
  data_sources: 'External data sources status',
};

export default function VerificationPanel() {
  const [checks, setChecks] = useState([]);
  const [overallStatus, setOverallStatus] = useState(null);
  const [runAt, setRunAt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [autoRun, setAutoRun] = useState(false);

  useEffect(() => {
    if (autoRun) {
      runChecks();
      const interval = setInterval(runChecks, 60000); // Auto-run every minute
      return () => clearInterval(interval);
    }
  }, [autoRun]);

  async function runChecks() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/panel/verification/run`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setChecks(data.checks || []);
        setOverallStatus(data.overall_status);
        setRunAt(data.run_at);
      }
    } catch (err) {
      console.error('Verification error:', err);
      setOverallStatus('unreachable');
    }
    setLoading(false);
  }

  const statusColors = {
    healthy: { bg: 'var(--green-light)', border: 'var(--green-primary)', text: 'var(--green-dark)', icon: '✓' },
    degraded: { bg: '#fef9c3', border: '#d97706', text: '#92400e', icon: '⚠' },
    unhealthy: { bg: '#fef2f2', border: 'var(--error)', text: '#991b1b', icon: '✕' },
    unreachable: { bg: '#f3f4f6', border: 'var(--text-light)', text: 'var(--text-mid)', icon: '?' },
  };

  const currentStatus = statusColors[overallStatus] || statusColors.unreachable;

  const passCount = checks.filter(c => c.status === 'pass').length;
  const failCount = checks.filter(c => c.status === 'fail').length;
  const skipCount = checks.filter(c => c.status === 'skip').length;

  return (
    <section className="verification-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <h2 style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)' }}>
            🔍 System Verification
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.4rem' }}>
            Run health checks to verify all system components are operational.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-mid)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={autoRun}
              onChange={e => setAutoRun(e.target.checked)}
            />
            Auto-refresh
          </label>
          <button
            onClick={runChecks}
            disabled={loading}
            style={{
              padding: '0.75rem 1.5rem',
              borderRadius: '12px',
              background: loading ? 'var(--text-light)' : 'var(--green-primary)',
              color: 'white',
              border: 'none',
              fontFamily: 'Nunito',
              fontWeight: 800,
              fontSize: '0.9rem',
              cursor: loading ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            {loading ? (
              <>
                <span style={{ width: 14, height: 14, border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                Running...
              </>
            ) : (
              'Run All Checks'
            )}
          </button>
        </div>
      </div>

      {/* Overall status badge */}
      {overallStatus && (
        <div
          style={{
            background: currentStatus.bg,
            border: `2px solid ${currentStatus.border}`,
            borderRadius: '18px',
            padding: '1.5rem',
            marginBottom: '1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                background: currentStatus.border,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.5rem',
                color: 'white',
              }}
            >
              {currentStatus.icon}
            </div>
            <div>
              <div style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.25rem', color: currentStatus.text, textTransform: 'uppercase' }}>
                {overallStatus}
              </div>
              <div style={{ fontSize: '0.85rem', color: currentStatus.text }}>
                {passCount} passed · {failCount} failed · {skipCount} skipped
              </div>
            </div>
          </div>
          {runAt && (
            <div style={{ fontSize: '0.8rem', color: currentStatus.text }}>
              Last run: {new Date(runAt).toLocaleTimeString()}
            </div>
          )}
        </div>
      )}

      {/* Check results */}
      {checks.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {checks.map(check => (
            <CheckRow key={check.name} check={check} />
          ))}
        </div>
      ) : (
        <div
          style={{
            textAlign: 'center',
            padding: '4rem',
            background: 'var(--gray-bg)',
            borderRadius: '18px',
            border: '1.5px solid var(--border)',
          }}
        >
          <p style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-mid)' }}>
            No checks run yet
          </p>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.5rem' }}>
            Click "Run All Checks" to verify system health
          </p>
        </div>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </section>
  );
}

function CheckRow({ check }) {
  const { name, status, message, latency_ms } = check;

  const statusConfig = {
    pass: { bg: 'var(--green-light)', border: 'var(--green-primary)', color: 'var(--green-dark)', icon: '✓' },
    fail: { bg: '#fef2f2', border: 'var(--error)', color: '#991b1b', icon: '✕' },
    skip: { bg: '#f3f4f6', border: 'var(--text-light)', color: 'var(--text-mid)', icon: '–' },
  };

  const config = statusConfig[status] || statusConfig.skip;
  const icon = CHECK_ICONS[name] || '•';
  const description = CHECK_DESCRIPTIONS[name] || name;

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '1rem 1.25rem',
        background: 'var(--white)',
        borderRadius: '14px',
        border: '1.5px solid var(--border)',
        borderLeft: `4px solid ${config.border}`,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <span style={{ fontSize: '1.25rem' }}>{icon}</span>
        <div>
          <div style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>
            {name.replace(/_/g, ' ')}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-light)' }}>
            {message}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {latency_ms != null && (
          <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-light)' }}>
            {latency_ms}ms
          </span>
        )}
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: config.bg,
            border: `2px solid ${config.border}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 900,
            fontSize: '0.85rem',
            color: config.color,
          }}
        >
          {config.icon}
        </div>
      </div>
    </div>
  );
}
