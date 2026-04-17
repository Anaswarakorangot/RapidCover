// frontend/src/components/admin/InstantReplayPanel.jsx
import { useState, useEffect } from 'react';
import { adminFetch } from '../../services/adminApi';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export default function InstantReplayPanel() {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchScenarios();
  }, []);

  async function fetchScenarios() {
    try {
      const res = await adminFetch(`${API_BASE}/admin/panel/drills/instant-replay/scenarios`);
      const data = await res.json();
      setScenarios(data.scenarios || []);
      if (data.scenarios?.length > 0) {
        setSelectedScenario(data.scenarios[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch scenarios:', err);
      setError('Failed to load scenarios list');
    }
  }

  async function handleRunSimulation() {
    if (!selectedScenario) return;

    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const res = await adminFetch(`${API_BASE}/admin/panel/drills/instant-replay`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          scenario_name: selectedScenario
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Simulation failed');
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error('Simulation error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="instant-replay-panel">
      <div className="admin-card">
        <div className="admin-card__header">
          <div className="admin-card__title">
            <span style={{ fontSize: '1.2rem', marginRight: '0.5rem' }}>🔄</span>
            Instant Replay System
          </div>
          <div className="admin-card__subtitle">
            Execute scripted historical scenarios for end-to-end demonstration.
          </div>
        </div>

        <div className="admin-card__body">
          <div className="replay-controls" style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', marginBottom: '2rem' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-muted)' }}>
                SELECT SCENARIO
              </label>
              <select 
                className="admin-input"
                style={{ width: '100%', padding: '0.75rem' }}
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
                disabled={loading}
              >
                {scenarios.map(s => (
                  <option key={s.id} value={s.id}>{s.label}</option>
                ))}
              </select>
            </div>
            <button 
              className={`admin-btn admin-btn--primary ${loading ? 'admin-btn--loading' : ''}`}
              onClick={handleRunSimulation}
              disabled={loading || !selectedScenario}
              style={{ padding: '0.75rem 2rem', height: 'fit-content' }}
            >
              {loading ? 'Processing...' : 'Run Simulation'}
            </button>
          </div>

          {selectedScenario && (
            <div className="scenario-description" style={{ background: 'var(--bg-light)', padding: '1rem', borderRadius: '8px', marginBottom: '2rem', borderLeft: '4px solid var(--primary)' }}>
              <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-dark)' }}>
                {scenarios.find(s => s.id === selectedScenario)?.description}
              </p>
            </div>
          )}

          {error && (
            <div className="admin-alert admin-alert--danger" style={{ marginBottom: '2rem' }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {result && (
            <div className="replay-results animate-fade-in shadow-sm" style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '1.5rem', borderRadius: '12px' }}>
              <h4 style={{ color: '#166534', marginTop: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                ✅ Simulation Successful
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.9rem' }}>
                <div style={{ color: '#166534' }}>
                  <strong>Trigger ID:</strong> #{result.trigger_id}<br />
                  <strong>Target Zone:</strong> {result.zone_code}
                </div>
                <div style={{ color: '#166534' }}>
                  <strong>Claims Created:</strong> {result.claims_created}<br />
                  <strong>Processed At:</strong> {new Date().toLocaleTimeString()}
                </div>
              </div>
              <div style={{ marginTop: '1rem', fontSize: '0.8rem', fontStyle: 'italic', color: '#15803d' }}>
                You can now head over to the <strong>Fraud Queue</strong> or <strong>Payments</strong> tabs to see the resulting claims and their validation matrix.
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="admin-card" style={{ marginTop: '2rem' }}>
        <div className="admin-card__header">
          <div className="admin-card__title">How it works</div>
        </div>
        <div className="admin-card__body">
          <ul style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: '1.6' }}>
            <li><strong>Atomic Injection:</strong> Unlike standard drills, Instant Replay injects the final `TriggerEvent` directly with pre-verified historical parameters.</li>
            <li><strong>Full Exhaustion:</strong> It immediately runs the `claims_processor` for all active policies in the zone at the time of the event.</li>
            <li><strong>Audit Readiness:</strong> Every claim generated has a full 10-point validation matrix and a unique transaction log.</li>
            <li><strong>Fraud Synthesis:</strong> Some scenarios include deliberate GPS spoofing clusters to demonstrate our ML-based fraud detection.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
