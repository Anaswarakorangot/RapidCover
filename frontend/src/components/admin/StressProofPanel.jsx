// frontend/src/components/admin/StressProofPanel.jsx
// Dynamic stress scenarios — fetches live data from backend

import React, { useState, useEffect } from 'react';
import { AdminLoader, AdminError, AdminEmpty, ProofCard, SourceBadge } from './AdminProofShared';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const BADGE_MAP = {
  monsoon: { bg: '#dbeafe', color: '#2563eb', label: 'Monsoon' },
  aqi:     { bg: '#ffedd5', color: '#ea580c', label: 'AQI' },
  bandh:   { bg: '#f3e8ff', color: '#9333ea', label: 'Bandh' },
  combo:   { bg: '#fee2e2', color: '#dc2626', label: 'Combo' },
};

function getBadge(name) {
  const n = name.toLowerCase();
  if (n.includes('monsoon') && n.includes('heat')) return BADGE_MAP.combo;
  if (n.includes('monsoon')) return BADGE_MAP.monsoon;
  if (n.includes('aqi'))     return BADGE_MAP.aqi;
  if (n.includes('bandh'))   return BADGE_MAP.bandh;
  return { bg: 'var(--gray-bg)', color: 'var(--text-mid)', label: 'Scenario' };
}

function formatRs(val) {
  if (val >= 100000) return `₹${(val / 100000).toFixed(2)}L`;
  if (val >= 1000) return `₹${(val / 1000).toFixed(1)}K`;
  return `₹${val}`;
}

export default function StressProofPanel() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [expanded, setExpanded] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/admin/panel/stress-scenarios`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <AdminLoader message="Computing stress scenarios…" />;
  if (error)   return <AdminError message={error} onRetry={load} />;
  if (!data?.scenarios?.length) return <AdminEmpty icon="⚡" message="No stress scenarios configured" />;

  const scenarios = data.scenarios;
  const totalReserve = data.total_reserve_needed || 0;
  const computedAt = data.computed_at;

  return (
    <ProofCard
      title="⚡ Stress Scenario Proof"
      subtitle={`${scenarios.length} scenarios — actuarial reserve calculations from live data`}
      timestamp={computedAt}
      source={scenarios.some(s => s.data_source === 'live') ? 'live' : 'mock'}
      passFail={totalReserve >= 0 ? 'pass' : 'fail'}
    >
      {/* Summary bar */}
      <div className="proof-summary-bar" style={{ marginBottom: '1.5rem' }}>
        <div className="proof-summary-item">
          <span className="proof-summary-label">Scenarios</span>
          <span className="proof-summary-value">{scenarios.length}</span>
        </div>
        <div className="proof-summary-item">
          <span className="proof-summary-label">Total Reserve Needed</span>
          <span className="proof-summary-value" style={{ color: totalReserve > 0 ? 'var(--error)' : 'var(--green-primary)' }}>
            {formatRs(totalReserve)}
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="proof-table-wrapper">
        <table className="proof-table">
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Days</th>
              <th style={{ textAlign: 'right' }}>Projected Claims</th>
              <th style={{ textAlign: 'right' }}>Projected Payout</th>
              <th style={{ textAlign: 'right' }}>City Reserve</th>
              <th style={{ textAlign: 'right' }}>Reserve Gap</th>
              <th>Source</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map(s => {
              const badge = getBadge(s.scenario_name);
              const isOpen = expanded === s.scenario_id;
              return (
                <React.Fragment key={s.scenario_id}>
                  <tr className={isOpen ? 'proof-row--open' : ''}>
                    <td>
                      <span className="proof-type-badge" style={{ background: badge.bg, color: badge.color }}>{badge.label}</span>
                      <span style={{ marginLeft: '0.5rem', fontWeight: 700, fontSize: '0.85rem' }}>{s.scenario_name}</span>
                    </td>
                    <td>{s.days}d</td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>{s.projected_claims.toLocaleString()}</td>
                    <td style={{ textAlign: 'right', fontWeight: 900 }}>{formatRs(s.projected_payout)}</td>
                    <td style={{ textAlign: 'right' }}>{formatRs(s.city_reserve_available)}</td>
                    <td style={{ textAlign: 'right', fontWeight: 900, color: s.reserve_needed > 0 ? 'var(--error)' : 'var(--green-primary)' }}>
                      {formatRs(s.reserve_needed)}
                    </td>
                    <td><SourceBadge source={s.data_source} /></td>
                    <td>
                      <button className="proof-expand-btn" onClick={() => setExpanded(isOpen ? null : s.scenario_id)}
                        style={{ transform: isOpen ? 'rotate(180deg)' : 'none' }}>▼</button>
                    </td>
                  </tr>
                  {isOpen && (
                    <tr className="proof-detail-row">
                      <td colSpan={8}>
                        <div className="proof-detail-card">
                          <p className="proof-detail-section-label">FORMULA BREAKDOWN</p>
                          <div className="proof-formula-grid">
                            {Object.entries(s.formula_breakdown || {}).filter(([k]) => k.startsWith('step_')).map(([key, val]) => (
                              <div key={key} className="proof-formula-step">
                                <span className="proof-formula-step__label">{key.replace(/_/g, ' ').replace('step ', 'Step ')}</span>
                                <code className="proof-formula-step__value">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</code>
                              </div>
                            ))}
                          </div>

                          <p className="proof-detail-section-label" style={{ marginTop: '1rem' }}>ASSUMPTIONS</p>
                          <ul className="proof-assumptions-list">
                            {(s.assumptions || []).map((a, i) => (
                              <li key={i}>{a}</li>
                            ))}
                          </ul>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Exposure bar chart */}
      <div className="proof-exposure-chart" style={{ marginTop: '2rem' }}>
        <p style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1rem', marginBottom: '1rem' }}>
          Reserve Gap Distribution
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {scenarios.map(s => {
            const maxReserve = Math.max(...scenarios.map(x => x.reserve_needed), 1);
            const pct = Math.max(2, Math.round((s.reserve_needed / maxReserve) * 100));
            const badge = getBadge(s.scenario_name);
            return (
              <div key={s.scenario_id} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{ width: 180, fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-mid)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {s.scenario_name}
                </span>
                <div style={{ flex: 1, height: 10, background: 'var(--gray-bg)', borderRadius: 5, overflow: 'hidden' }}>
                  <div style={{ width: `${pct}%`, height: '100%', background: badge.color, borderRadius: 5, transition: 'width 1s ease' }} />
                </div>
                <span style={{ width: 80, fontSize: '0.8rem', fontWeight: 900, textAlign: 'right' }}>{formatRs(s.reserve_needed)}</span>
              </div>
            );
          })}
        </div>
      </div>
    </ProofCard>
  );
}
