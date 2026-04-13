// frontend/src/components/admin/BCRPanel.jsx
// BCR (Burning Cost Rate) / Loss Ratio monitoring per city
// Reads from Person 2's BCR endpoint: GET /api/v1/admin/panel/bcr
// BCR = total_claims_paid / total_premiums_collected | Target: 0.55 - 0.70
// Loss Ratio > 85% -> suspend new enrolments (toggle in admin)
// Loss Ratio > 100% -> reinsurance treaty activation alert

import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

function lrColor(lr) {
  if (lr > 100) return 'var(--error)';
  if (lr > 85) return 'var(--warning)';
  if (lr > 70) return '#f59e0b';
  return 'var(--green-primary)';
}

function lrLabel(lr) {
  if (lr > 100) return '🚨 REINSURANCE';
  if (lr > 85) return '🛑 SUSPENDED';
  if (lr > 70) return '⚠️ WATCH';
  return '✅ HEALTHY';
}

function BCRBar({ lr }) {
  const pct = Math.min(lr, 130);
  return (
    <div className="bcr-bar-track">
      {/* Target band 55-70% */}
      <div className="bcr-bar-target" style={{ left: '42%', width: '11.5%', background: 'rgba(61,184,92,0.2)', height: '100%', position: 'absolute', borderRadius: '4px' }} title="Target BCR 0.55-0.70" />
      {/* 85% line */}
      <div className="bcr-bar-threshold" style={{ left: '65.4%', background: 'var(--warning)', width: '2px', height: '18px', top: '-4px', position: 'absolute' }} title="85% suspension threshold" />
      {/* 100% line */}
      <div className="bcr-bar-threshold bcr-bar-threshold--red" style={{ left: '76.9%', background: 'var(--error)', width: '2px', height: '18px', top: '-4px', position: 'absolute' }} title="100% reinsurance threshold" />
      <div
        className="bcr-bar-fill"
        style={{ width: `${(pct / 130) * 100}%`, background: lrColor(lr) }}
      />
    </div>
  );
}

export default function BCRPanel() {
  const [cities, setCities] = useState([]);
  const [overrides, setOverrides] = useState({}); // manual override state keyed by city code
  const [loading, setLoading] = useState(true);
  const [reinsAlert, setReinsAlert] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchBCR();
    const t = setInterval(fetchBCR, 30000);
    return () => clearInterval(t);
  }, []);

  async function fetchBCR() {
    setError(false);
    try {
      const res = await fetch(`${API_BASE}/admin/panel/bcr`);
      if (res.ok) {
        const data = await res.json();
        // Expect: { cities: [{city, code, premiums, claims, lr, suspended, pool_cap_pct}] }
        setCities(data.cities || []);
      } else {
        setCities([]);
        setError(true);
      }
    } catch {
      setCities([]);
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  // Merge backend state with local manual overrides
  const displayCities = cities.map(c => ({
    ...c,
    suspended: overrides[c.code] !== undefined ? overrides[c.code] : c.suspended,
  }));

  // Reinsurance alert: any city > 120% pool cap
  useEffect(() => {
    setReinsAlert(displayCities.some(c => c.pool_cap_pct > 120));
  }, [displayCities]);

  async function toggleSuspension(code, currentVal) {
    const newVal = !currentVal;
    setOverrides(prev => ({ ...prev, [code]: newVal }));

    // Optimistically patch backend
    try {
      await fetch(`${API_BASE}/admin/panel/bcr/suspend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ city_code: code, suspended: newVal }),
      });
    } catch {
      // Backend not yet wired -- local override stays
    }
  }

  const totalPremiums = displayCities.reduce((a, c) => a + c.premiums, 0);
  const totalClaims = displayCities.reduce((a, c) => a + c.claims, 0);
  const overallLR = totalPremiums > 0 ? Math.round((totalClaims / totalPremiums) * 100) : 0;

  return (
    <section className="bcr-panel">
      {/* Reinsurance activation alert */}
      {reinsAlert && (
        <div
          className="bcr-reins-alert"
          style={{
            background: '#fee2e2',
            border: '1.5px solid var(--error)',
            borderRadius: '18px',
            padding: '1.25rem',
            marginBottom: '1.5rem',
            display: 'flex',
            gap: '1rem',
            alignItems: 'center',
            color: '#991b1b'
          }}
        >
          <span style={{ fontSize: '2rem' }}>🚨</span>
          <div>
            <strong style={{ fontFamily: 'Nunito', fontSize: '1.1rem' }}>Reinsurance Activation Alert</strong>
            <p style={{ fontSize: '0.9rem', margin: '0.25rem 0 0' }}>One or more cities have crossed 120% of city weekly premium pool cap. Reinsurance treaty review required.</p>
          </div>
        </div>
      )}

      <div className="bcr-panel__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <h2 className="bcr-panel__title" style={{ fontFamily: 'Nunito', fontWeight: 900, color: 'var(--text-dark)' }}>BCR / Loss Ratio</h2>
          <p className="bcr-panel__subtitle" style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.4rem' }}>
            BCR = claims paid / premiums collected &nbsp;&middot;&nbsp; Target: 0.55-0.70 &nbsp;&middot;&nbsp; Overall: <strong style={{ color: lrColor(overallLR) }}>{overallLR}%</strong>
          </p>
        </div>
        <div className="bcr-legend" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          {[
            { c: 'var(--green-primary)', l: 'Healthy <70%' },
            { c: '#ffc107', l: 'Watch 70-85%' },
            { c: 'var(--warning)', l: 'Suspended >85%' },
            { c: 'var(--error)', l: 'Reinsurance >100%' },
          ].map(leg => (
            <span key={leg.l} style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-mid)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: leg.c }} />
              {leg.l}
            </span>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="bcr-empty" style={{ textAlign: 'center', padding: '3rem 0', background: 'var(--gray-bg)', borderRadius: '24px', border: '1.5px solid var(--border)' }}>
          <p style={{ fontFamily: 'Nunito', fontWeight: 800, fontSize: '1.2rem', color: 'var(--text-mid)' }}>Loading BCR metrics...</p>
        </div>
      ) : displayCities.length === 0 ? (
        <div className="bcr-empty" style={{ textAlign: 'center', padding: '3rem 0', background: 'var(--gray-bg)', borderRadius: '24px', border: '1.5px solid var(--border)' }}>
          <p style={{ fontFamily: 'Nunito', fontWeight: 800, fontSize: '1.2rem', color: 'var(--text-mid)' }}>No city BCR data yet</p>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.5rem' }}>
            {error ? 'The BCR endpoint is unavailable right now.' : 'This panel will populate once premiums and paid claims exist.'}
          </p>
        </div>
      ) : (
      <div className="bcr-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' }}>
        {displayCities.map(c => {
          const bcr = (c.lr / 100).toFixed(2);
          const color = lrColor(c.lr);
          const label = lrLabel(c.lr);
          const isAutoSuspend = c.lr > 85 && overrides[c.code] === undefined;
          const isManuallySuspended = overrides[c.code] === true && c.lr <= 85;
          const isManuallyResumed = overrides[c.code] === false && c.lr > 85;

          return (
            <div key={c.code} className={`bcr-card ${c.suspended ? 'bcr-card--suspended' : ''}`}>
              <div className="bcr-card__top" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <p className="bcr-card__city" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.25rem' }}>{c.city}</p>
                  <code className="bcr-card__code" style={{ fontSize: '0.75rem', background: 'var(--gray-bg)', padding: '0.2rem 0.5rem', borderRadius: '6px', color: 'var(--text-light)' }}>{c.code}</code>
                </div>
                <span className="bcr-card__badge" style={{ fontSize: '0.7rem', fontWeight: 800, padding: '0.4rem 0.75rem', borderRadius: '12px', background: color + '15', color, border: `1px solid ${color}30` }}>
                  {label}
                </span>
              </div>

              <div className="bcr-card__numbers" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', margin: '1.5rem 0 1rem' }}>
                {[
                  { l: 'Loss Ratio', v: `${c.lr}%`, cl: color },
                  { l: 'BCR', v: bcr, cl: 'var(--text-dark)' },
                  { l: 'Pool cap', v: `${c.pool_cap_pct}%`, cl: c.pool_cap_pct > 120 ? 'var(--error)' : c.pool_cap_pct > 100 ? 'var(--warning)' : 'var(--text-dark)' }
                ].map(stat => (
                  <div key={stat.l} style={{ background: 'var(--gray-bg)', borderRadius: '12px', padding: '0.75rem', textAlign: 'center' }}>
                    <p style={{ fontSize: '0.65rem', color: 'var(--text-light)', textTransform: 'uppercase', fontWeight: 700 }}>{stat.l}</p>
                    <p style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.1rem', color: stat.cl, marginTop: '2px' }}>{stat.v}</p>
                  </div>
                ))}
              </div>

              <BCRBar lr={c.lr} />

              <div className="bcr-card__footer" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-mid)', marginBottom: '1.25rem' }}>
                <span>Premiums: ₹{(c.premiums / 100000).toFixed(1)}L</span>
                <span>Claims: ₹{(c.claims / 100000).toFixed(1)}L</span>
              </div>

              {/* Suspension toggle */}
              <div className="bcr-toggle-row" style={{ borderTop: '1.5px solid var(--border)', paddingTop: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="bcr-toggle-info" style={{ flex: 1 }}>
                  {isAutoSuspend && <p style={{ fontSize: '0.7rem', color: 'var(--error)', fontWeight: 700 }}>⚠️ Auto-suspended (LR &gt;85%)</p>}
                  {isManuallySuspended && <p style={{ fontSize: '0.7rem', color: 'var(--warning)', fontWeight: 700 }}>ℹ️ Manually suspended</p>}
                  {isManuallyResumed && <p style={{ fontSize: '0.7rem', color: 'var(--error)', fontWeight: 700 }}>🚨 Manual override - LR &gt;85%</p>}
                  <p style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-mid)' }}>
                    {c.suspended ? 'Enrolments frozen' : 'Active'}
                  </p>
                </div>
                <button
                  className={`bcr-toggle-btn ${c.suspended ? 'bcr-toggle-btn--resume' : 'bcr-toggle-btn--suspend'}`}
                  onClick={() => toggleSuspension(c.code, c.suspended)}
                  style={{ fontFamily: 'Nunito', fontWeight: 800, minWidth: '90px' }}
                >
                  {c.suspended ? 'Resume' : 'Suspend'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
      )}
    </section>
  );
}
