import { useState, useEffect } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function DemoModePanel() {
  const [demoStatus, setDemoStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [zones, setZones] = useState([]);
  const [creatingTrigger, setCreatingTrigger] = useState(false);
  const [triggerForm, setTriggerForm] = useState({
    zone_id: '',
    trigger_type: 'rain',
    severity: 4
  });

  useEffect(() => {
    loadStatus();
    loadZones();
  }, []);

  const loadStatus = async () => {
    try {
      const res = await fetch(`${API}/admin/panel/demo-mode/status`);
      if (res.ok) {
        const data = await res.json();
        setDemoStatus(data);
      }
    } catch (err) {
      console.error('Failed to load demo mode status:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadZones = async () => {
    try {
      const res = await fetch(`${API}/zones`);
      if (res.ok) {
        const data = await res.json();
        setZones(data);
      }
    } catch (err) {
      console.error('Failed to load zones:', err);
    }
  };

  const handleToggle = async () => {
    setToggling(true);
    try {
      const res = await fetch(`${API}/admin/panel/demo-mode/toggle?enabled=${!demoStatus.enabled}`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setDemoStatus(data);
      }
    } catch (err) {
      console.error('Failed to toggle demo mode:', err);
      alert('Failed to toggle demo mode');
    } finally {
      setToggling(false);
    }
  };

  const handleCreateTrigger = async (e) => {
    e.preventDefault();
    if (!triggerForm.zone_id) {
      alert('Please select a zone');
      return;
    }

    setCreatingTrigger(true);
    try {
      const res = await fetch(
        `${API}/admin/panel/demo-mode/create-trigger?zone_id=${triggerForm.zone_id}&trigger_type=${triggerForm.trigger_type}&severity=${triggerForm.severity}`,
        { method: 'POST' }
      );

      const data = await res.json();

      if (res.ok && data.status === 'success') {
        alert(`✅ ${data.message}\n\nTrigger ID: ${data.trigger.id}\nClaims created: ${data.claims_created}`);
        // Reset form
        setTriggerForm({ zone_id: '', trigger_type: 'rain', severity: 4 });
      } else {
        alert(`❌ ${data.error || 'Failed to create trigger'}`);
      }
    } catch (err) {
      console.error('Failed to create trigger:', err);
      alert('Failed to create trigger');
    } finally {
      setCreatingTrigger(false);
    }
  };

  if (loading || !demoStatus) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-mid)' }}>Loading...</p>
      </div>
    );
  }

  const isEnabled = demoStatus.enabled;

  return (
    <div className="demo-mode-panel" style={{ maxWidth: '900px', margin: '0 auto' }}>
      {/* Demo Mode Toggle Card */}
      <div style={{
        background: isEnabled ? '#fef3c7' : 'white',
        border: `2px solid ${isEnabled ? '#f59e0b' : 'var(--border)'}`,
        borderRadius: '20px',
        padding: '2rem',
        marginBottom: '2rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1.5rem' }}>
          <div>
            <h2 style={{
              fontFamily: 'Nunito',
              fontSize: '1.5rem',
              fontWeight: 900,
              color: isEnabled ? '#92400e' : 'var(--text-dark)',
              marginBottom: '0.5rem'
            }}>
              {isEnabled ? '🎭 Demo Override Mode Active' : '📊 Production Mode'}
            </h2>
            <p style={{ color: isEnabled ? '#78350f' : 'var(--text-mid)', fontSize: '0.9rem', lineHeight: 1.6 }}>
              {demoStatus.description}
            </p>
          </div>

          <button
            onClick={handleToggle}
            disabled={toggling}
            style={{
              background: isEnabled ? '#ef4444' : 'var(--green-primary)',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
              padding: '1rem 2rem',
              fontSize: '1rem',
              fontWeight: 700,
              cursor: toggling ? 'not-allowed' : 'pointer',
              opacity: toggling ? 0.6 : 1,
              transition: 'all 0.2s',
              whiteSpace: 'nowrap'
            }}
          >
            {toggling ? 'Switching...' : (isEnabled ? 'Disable Demo Mode' : 'Enable Demo Mode')}
          </button>
        </div>

        {isEnabled && demoStatus.bypasses_active && (
          <div style={{
            padding: '1rem',
            background: '#fffbeb',
            border: '1px solid #fbbf24',
            borderRadius: '12px'
          }}>
            <p style={{ fontSize: '0.85rem', color: '#78350f', margin: 0, marginBottom: '0.75rem', fontWeight: 700 }}>
              ⚠️ Active Bypasses (works on REAL database):
            </p>
            <div style={{ display: 'grid', gap: '0.5rem', fontSize: '0.85rem', color: '#92400e' }}>
              {demoStatus.bypasses_active.adverse_selection && (
                <div>✓ Adverse selection blocking disabled (can buy policy during active events)</div>
              )}
              {demoStatus.bypasses_active.activity_gate && (
                <div>✓ 7-day activity gate disabled (can buy policy immediately after registration)</div>
              )}
              {demoStatus.bypasses_active.fraud_rejection && (
                <div>✓ Fraud auto-rejection disabled (high fraud score claims allowed)</div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Manual Trigger Creation */}
      {isEnabled && (
        <div style={{
          background: 'white',
          border: '1.5px solid var(--border)',
          borderRadius: '20px',
          padding: '2rem',
          marginBottom: '2rem'
        }}>
          <h3 style={{
            fontFamily: 'Nunito',
            fontSize: '1.2rem',
            fontWeight: 800,
            marginBottom: '1rem',
            color: 'var(--text-dark)'
          }}>
            🎯 Manual Trigger Creation
          </h3>

          <p style={{ fontSize: '0.9rem', color: 'var(--text-mid)', marginBottom: '1.5rem', lineHeight: 1.6 }}>
            Create REAL trigger events in the database. This will generate REAL claims for partners with active policies in the selected zone.
          </p>

          <form onSubmit={handleCreateTrigger} style={{ display: 'grid', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-dark)' }}>
                Zone
              </label>
              <select
                value={triggerForm.zone_id}
                onChange={(e) => setTriggerForm({ ...triggerForm, zone_id: e.target.value })}
                required
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '12px',
                  border: '1.5px solid var(--border)',
                  fontSize: '0.9rem',
                  fontFamily: 'Nunito'
                }}
              >
                <option value="">Select a zone...</option>
                {zones.map(zone => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name} ({zone.code}) - {zone.city}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-dark)' }}>
                Trigger Type
              </label>
              <select
                value={triggerForm.trigger_type}
                onChange={(e) => setTriggerForm({ ...triggerForm, trigger_type: e.target.value })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '12px',
                  border: '1.5px solid var(--border)',
                  fontSize: '0.9rem',
                  fontFamily: 'Nunito'
                }}
              >
                <option value="rain">🌧️ Heavy Rain</option>
                <option value="heat">🌡️ Extreme Heat</option>
                <option value="aqi">💨 Dangerous AQI</option>
                <option value="shutdown">🚫 Civic Shutdown</option>
                <option value="closure">🏪 Store Closure</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-dark)' }}>
                Severity (3+ blocks new enrollments)
              </label>
              <input
                type="number"
                min="1"
                max="5"
                value={triggerForm.severity}
                onChange={(e) => setTriggerForm({ ...triggerForm, severity: parseInt(e.target.value) })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '12px',
                  border: '1.5px solid var(--border)',
                  fontSize: '0.9rem',
                  fontFamily: 'Nunito'
                }}
              />
            </div>

            <button
              type="submit"
              disabled={creatingTrigger}
              style={{
                background: creatingTrigger ? 'var(--text-mid)' : 'var(--green-primary)',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                padding: '1rem',
                fontSize: '1rem',
                fontWeight: 700,
                cursor: creatingTrigger ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {creatingTrigger ? 'Creating...' : 'Create Trigger Event'}
            </button>
          </form>
        </div>
      )}

      {/* Instructions */}
      <div style={{
        background: '#f0fdf4',
        border: '1.5px solid #86efac',
        borderRadius: '20px',
        padding: '1.5rem'
      }}>
        <h4 style={{
          fontFamily: 'Nunito',
          fontSize: '1rem',
          fontWeight: 800,
          marginBottom: '0.75rem',
          color: '#166534'
        }}>
          💡 How to Use Demo Mode
        </h4>

        <ul style={{ fontSize: '0.85rem', color: '#14532d', lineHeight: 1.8, paddingLeft: '1.5rem' }}>
          <li>Enable demo mode to bypass restrictions and demonstrate features</li>
          <li>Create manual trigger events to showcase automated claim generation</li>
          <li>All data is REAL - stored in the actual database with real partners</li>
          <li>Demo mode allows policy purchase during active events (bypasses adverse selection)</li>
          <li>New users can buy policies immediately (bypasses 7-day activity requirement)</li>
          <li>Remember to disable demo mode when done to restore production safeguards</li>
        </ul>
      </div>
    </div>
  );
}
