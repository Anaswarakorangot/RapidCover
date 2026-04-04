/**
 * PartialDisruptionPanel.jsx — Partial Disruption Mode Admin Panel
 *
 * Shows disruption categories, allows simulation with partial disruption parameters,
 * and displays payout factor breakdown.
 */

import { useState, useEffect } from 'react';
import { getAllZones, simulateWeather, simulateAqi } from '../../services/adminApi';

/* ─── Disruption Category Config ─────────────────────────────────────────── */
const CATEGORIES = [
  {
    key: 'full_halt',
    label: 'Full Halt',
    factor: '100%',
    factorNum: 1.0,
    description: 'Complete work stoppage — no deliveries possible',
    color: '#ef4444',
    bg: '#fee2e2',
    icon: '🛑',
    triggers: 'Severity 4–5, Shutdown, Closure',
  },
  {
    key: 'severe_reduction',
    label: 'Severe Reduction',
    factor: '75%',
    factorNum: 0.75,
    description: '75% income loss — most deliveries cancelled',
    color: '#f97316',
    bg: '#ffedd5',
    icon: '⚠️',
    triggers: 'Severity 3, or 70–90% order drop',
  },
  {
    key: 'moderate_reduction',
    label: 'Moderate Reduction',
    factor: '50%',
    factorNum: 0.50,
    description: '50% income loss — significant slowdown',
    color: '#eab308',
    bg: '#fef9c3',
    icon: '📉',
    triggers: 'Severity 2, or 40–70% order drop',
  },
  {
    key: 'minor_reduction',
    label: 'Minor Reduction',
    factor: '25%',
    factorNum: 0.25,
    description: '25% income loss — noticeable but manageable',
    color: '#3b82f6',
    bg: '#dbeafe',
    icon: '📊',
    triggers: 'Severity 1, or 20–40% order drop',
  },
];

/* ─── Payout Factor Visualizer ────────────────────────────────────────────── */
function FactorBar({ factor, label, color }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
      <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-mid)', width: 130, flexShrink: 0 }}>
        {label}
      </span>
      <div style={{
        flex: 1, height: 10, background: '#f1f5f1', borderRadius: 10, overflow: 'hidden',
      }}>
        <div style={{
          height: '100%', width: `${factor * 100}%`, background: color, borderRadius: 10,
          transition: 'width 0.8s ease',
        }} />
      </div>
      <span style={{ fontSize: '0.78rem', fontWeight: 900, color, width: 40, textAlign: 'right' }}>
        {(factor * 100).toFixed(0)}%
      </span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Main Component
   ═══════════════════════════════════════════════════════════════════════════ */
export default function PartialDisruptionPanel() {
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  const [triggerType, setTriggerType] = useState('rain');
  const [expectedOrders, setExpectedOrders] = useState('100');
  const [actualOrders, setActualOrders] = useState('30');
  const [factorOverride, setFactorOverride] = useState('');
  const [simResult, setSimResult] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const [useOrderData, setUseOrderData] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const z = await getAllZones();
        setZones(z || []);
        if (z?.length > 0) setSelectedZone(z[0].id);
      } catch { /* zones may not be seeded yet */ }
    })();
  }, []);

  async function handleSimulate() {
    if (!selectedZone) return;
    setSimulating(true);
    setSimResult(null);

    try {
      const params = {};

      if (useOrderData) {
        if (expectedOrders) params.expected_orders = parseInt(expectedOrders);
        if (actualOrders !== '') params.actual_orders = parseInt(actualOrders);
      }

      if (factorOverride && !useOrderData) {
        params.partial_factor_override = parseFloat(factorOverride);
      }

      let result;
      if (triggerType === 'rain') {
        result = await simulateWeather(selectedZone, { rainfall_mm_hr: 72, ...params });
      } else if (triggerType === 'aqi') {
        result = await simulateAqi(selectedZone, { aqi: 420, ...params });
      } else {
        result = await simulateWeather(selectedZone, { temp_celsius: 44, ...params });
      }

      setSimResult(result);
    } catch (err) {
      setSimResult({ error: err.message });
    }

    setSimulating(false);
  }

  // Calculate preview disruption category from current inputs
  function getPreviewCategory() {
    if (factorOverride && !useOrderData) {
      const override = parseFloat(factorOverride);
      if (override >= 1.0) return CATEGORIES[0];
      if (override >= 0.75) return CATEGORIES[1];
      if (override >= 0.50) return CATEGORIES[2];
      return CATEGORIES[3];
    }

    if (useOrderData && expectedOrders && actualOrders !== '') {
      const expected = parseInt(expectedOrders);
      const actual = parseInt(actualOrders);
      if (expected > 0) {
        const reduction = 1 - (actual / expected);
        if (reduction >= 0.90) return CATEGORIES[0];
        if (reduction >= 0.70) return CATEGORIES[1];
        if (reduction >= 0.40) return CATEGORIES[2];
        return CATEGORIES[3];
      }
    }

    return null;
  }

  const preview = getPreviewCategory();

  return (
    <div className="admin-section" style={{ animationDelay: '0.2s' }}>
      <div className="admin-section-label">PARTIAL DISRUPTION MODE</div>

      {/* Category Reference Cards */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
        gap: '0.75rem', marginBottom: '2rem',
      }}>
        {CATEGORIES.map(cat => (
          <div key={cat.key} style={{
            background: 'var(--white)', border: `1.5px solid ${cat.color}30`,
            borderLeft: `5px solid ${cat.color}`,
            borderRadius: 16, padding: '1rem 1.25rem',
            transition: 'all 0.2s',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '1.1rem' }}>{cat.icon}</span>
              <span style={{
                fontFamily: "'Nunito', sans-serif", fontWeight: 900, fontSize: '0.95rem',
                color: cat.color,
              }}>
                {cat.label}
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-mid)', margin: '0 0 0.5rem', lineHeight: 1.4 }}>
              {cat.description}
            </p>
            <div style={{
              fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-light)',
              background: 'var(--gray-bg)', padding: '3px 8px', borderRadius: 8,
              display: 'inline-block',
            }}>
              {cat.triggers}
            </div>
            <div style={{ marginTop: '0.5rem' }}>
              <FactorBar factor={cat.factorNum} label="Payout Factor" color={cat.color} />
            </div>
          </div>
        ))}
      </div>

      {/* Simulation with Partial Disruption */}
      <div style={{
        background: 'var(--white)', border: '1.5px solid var(--border)',
        borderRadius: 18, padding: '1.5rem', marginBottom: '1.5rem',
      }}>
        <div className="proof-detail-section-label">Simulate with Partial Disruption</div>

        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: '1rem', marginBottom: '1.25rem',
        }}>
          {/* Zone selector */}
          <div className="notif-control-group">
            <label className="notif-control-label">Zone</label>
            <select className="notif-select" value={selectedZone || ''} onChange={e => setSelectedZone(parseInt(e.target.value))}>
              {zones.map(z => (
                <option key={z.id} value={z.id}>{z.name} ({z.code})</option>
              ))}
            </select>
          </div>

          {/* Trigger type */}
          <div className="notif-control-group">
            <label className="notif-control-label">Trigger Type</label>
            <select className="notif-select" value={triggerType} onChange={e => setTriggerType(e.target.value)}>
              <option value="rain">🌧️ Heavy Rain</option>
              <option value="heat">🌡️ Extreme Heat</option>
              <option value="aqi">💨 Dangerous AQI</option>
            </select>
          </div>

          {/* Mode toggle */}
          <div className="notif-control-group">
            <label className="notif-control-label">Disruption Mode</label>
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <button
                className={`admin-tab ${useOrderData ? 'admin-tab--active' : ''}`}
                style={{ fontSize: '0.75rem', padding: '0.4rem 0.8rem' }}
                onClick={() => setUseOrderData(true)}
              >
                Order Data
              </button>
              <button
                className={`admin-tab ${!useOrderData ? 'admin-tab--active' : ''}`}
                style={{ fontSize: '0.75rem', padding: '0.4rem 0.8rem' }}
                onClick={() => setUseOrderData(false)}
              >
                Manual Override
              </button>
            </div>
          </div>
        </div>

        {/* Order data inputs */}
        {useOrderData ? (
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <div className="notif-control-group">
              <label className="notif-control-label">Expected Orders</label>
              <input
                type="number" min="0" className="notif-select" style={{ width: 120 }}
                value={expectedOrders} onChange={e => setExpectedOrders(e.target.value)}
              />
            </div>
            <div className="notif-control-group">
              <label className="notif-control-label">Actual Orders</label>
              <input
                type="number" min="0" className="notif-select" style={{ width: 120 }}
                value={actualOrders} onChange={e => setActualOrders(e.target.value)}
              />
            </div>
            {expectedOrders && actualOrders !== '' && parseInt(expectedOrders) > 0 && (
              <div className="notif-control-group">
                <label className="notif-control-label">Reduction</label>
                <span style={{
                  fontFamily: "'Nunito', sans-serif", fontWeight: 900, fontSize: '1.4rem',
                  color: 'var(--error)', padding: '0.2rem 0',
                }}>
                  {((1 - parseInt(actualOrders) / parseInt(expectedOrders)) * 100).toFixed(0)}%
                </span>
              </div>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <div className="notif-control-group">
              <label className="notif-control-label">Factor Override (0.0 – 1.0)</label>
              <input
                type="number" min="0" max="1" step="0.05" className="notif-select" style={{ width: 120 }}
                value={factorOverride} onChange={e => setFactorOverride(e.target.value)}
                placeholder="e.g. 0.75"
              />
            </div>
          </div>
        )}

        {/* Preview badge */}
        {preview && (
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: preview.bg, color: preview.color,
            border: `1.5px solid ${preview.color}30`,
            padding: '6px 14px', borderRadius: 12, fontSize: 12, fontWeight: 700, marginBottom: '1rem',
          }}>
            {preview.icon} Expected: {preview.label} ({preview.factor} payout)
          </div>
        )}

        {/* Simulate button */}
        <div>
          <button
            className="proof-action-btn"
            onClick={handleSimulate}
            disabled={simulating || !selectedZone}
            style={{ minWidth: 180 }}
          >
            {simulating ? '⏳ Simulating...' : '🚀 Run Simulation'}
          </button>
        </div>
      </div>

      {/* Simulation Result */}
      {simResult && (
        <div style={{
          background: simResult.error ? '#fef2f2' : 'var(--white)',
          border: `1.5px solid ${simResult.error ? '#fecaca' : 'var(--border)'}`,
          borderRadius: 18, padding: '1.5rem',
        }}>
          <div className="proof-detail-section-label">
            {simResult.error ? '❌ Simulation Error' : '✅ Simulation Result'}
          </div>

          {simResult.error ? (
            <p style={{ color: 'var(--error)', fontSize: '0.88rem' }}>{simResult.error}</p>
          ) : (
            <>
              <div className="proof-formula-grid">
                <div className="proof-formula-step">
                  <span className="proof-formula-step__label">Zone</span>
                  <span className="proof-formula-step__value">{simResult.zone_name}</span>
                </div>
                <div className="proof-formula-step">
                  <span className="proof-formula-step__label">Triggers Created</span>
                  <span className="proof-formula-step__value">{simResult.triggers_created?.length || 0}</span>
                </div>
                {simResult.partial_disruption && (
                  <>
                    <div className="proof-formula-step">
                      <span className="proof-formula-step__label">Expected Orders</span>
                      <span className="proof-formula-step__value">{simResult.partial_disruption.expected_orders ?? '—'}</span>
                    </div>
                    <div className="proof-formula-step">
                      <span className="proof-formula-step__label">Actual Orders</span>
                      <span className="proof-formula-step__value">{simResult.partial_disruption.actual_orders ?? '—'}</span>
                    </div>
                    {simResult.partial_disruption.partial_factor_override != null && (
                      <div className="proof-formula-step" style={{ background: '#fef9c3' }}>
                        <span className="proof-formula-step__label">Factor Override</span>
                        <span className="proof-formula-step__value">{simResult.partial_disruption.partial_factor_override}</span>
                      </div>
                    )}
                  </>
                )}
              </div>

              {simResult.triggers_created?.length > 0 && (
                <p style={{ fontSize: '0.82rem', color: 'var(--green-dark)', fontWeight: 700, marginTop: '1rem' }}>
                  ✅ {simResult.triggers_created.length} trigger(s) created and claims auto-processed
                </p>
              )}
            </>
          )}
        </div>
      )}

      {/* How it works */}
      <div style={{
        padding: '1.25rem', background: 'var(--gray-bg)', borderRadius: 16, marginTop: '1.5rem',
        fontSize: '0.88rem', color: 'var(--text-mid)', lineHeight: 1.6,
      }}>
        <p style={{ margin: '0 0 0.5rem', fontWeight: 700, color: 'var(--text-dark)' }}>How partial disruption works:</p>
        <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
          <li><strong>Severity-based mapping:</strong> Severity 4–5 → full halt, 3 → severe, 2 → moderate, 1 → minor</li>
          <li><strong>Order data:</strong> If expected/actual orders are provided, reduction ratio determines category</li>
          <li><strong>Factor override:</strong> Explicit override (0.0–1.0) for testing</li>
          <li><strong>Shutdown/Closure:</strong> Always treated as full halt regardless of other data</li>
          <li>Payout = Base hourly rate × Severity multiplier × <strong>Partial disruption factor</strong> × Policy limits</li>
        </ul>
      </div>

      {/* Footer */}
      <div className="proof-card__footer">
        Disruption categories: full_halt (100%) · severe_reduction (75%) · moderate_reduction (50%) · minor_reduction (25%)
      </div>
    </div>
  );
}
