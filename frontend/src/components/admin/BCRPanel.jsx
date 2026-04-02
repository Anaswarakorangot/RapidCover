// frontend/src/components/admin/BCRPanel.jsx
// BCR (Burning Cost Rate) / Loss Ratio monitoring per city
// Reads from Person 2's BCR endpoint: GET /api/v1/admin/panel/bcr
// BCR = total_claims_paid / total_premiums_collected | Target: 0.55 - 0.70
// Loss Ratio > 85% -> suspend new enrolments (toggle in admin)
// Loss Ratio > 100% -> reinsurance treaty activation alert

import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Fallback demo data if endpoint not yet wired by Person 2
const DEMO_BCR_DATA = [
  { city: 'Bangalore', code: 'BLR', premiums: 310000, claims: 217000, lr: 70, suspended: false, pool_cap_pct: 78 },
  { city: 'Mumbai',    code: 'BOM', premiums: 380000, claims: 285000, lr: 75, suspended: false, pool_cap_pct: 85 },
  { city: 'Delhi NCR', code: 'DEL', premiums: 290000, claims: 261000, lr: 90, suspended: true,  pool_cap_pct: 102 },
  { city: 'Chennai',   code: 'CHN', premiums: 220000, claims: 127600, lr: 58, suspended: false, pool_cap_pct: 64 },
  { city: 'Hyderabad', code: 'HYD', premiums: 210000, claims: 117600, lr: 56, suspended: false, pool_cap_pct: 58 },
  { city: 'Kolkata',   code: 'KOL', premiums: 175000, claims: 112000, lr: 64, suspended: false, pool_cap_pct: 71 },
];

function lrColor(lr) {
  if (lr > 100) return '#dc3545';
  if (lr > 85)  return '#fd7e14';
  if (lr > 70)  return '#ffc107';
  return '#198754';
}

function lrLabel(lr) {
  if (lr > 100) return 'Reinsurance';
  if (lr > 85)  return 'Suspended';
  if (lr > 70)  return 'Watch';
  return 'Healthy';
}

function BCRBar({ lr }) {
  const pct = Math.min(lr, 130);
  return (
    <div className="bcr-bar-track">
      {/* Target band 55-70% */}
      <div className="bcr-bar-target" style={{ left: '42%', width: '11.5%' }} title="Target BCR 0.55-0.70" />
      {/* 85% line */}
      <div className="bcr-bar-threshold" style={{ left: '65.4%' }} title="85% suspension threshold" />
      {/* 100% line */}
      <div className="bcr-bar-threshold bcr-bar-threshold--red" style={{ left: '76.9%' }} title="100% reinsurance threshold" />
      <div
        className="bcr-bar-fill"
        style={{ width: `${(pct / 130) * 100}%`, background: lrColor(lr) }}
      />
    </div>
  );
}

export default function BCRPanel() {
  const [cities, setCities] = useState(DEMO_BCR_DATA);
  const [overrides, setOverrides] = useState({}); // manual override state keyed by city code
  const [loading, setLoading] = useState(true);
  const [reinsAlert, setReinsAlert] = useState(false);

  useEffect(() => {
    fetchBCR();
    const t = setInterval(fetchBCR, 30000);
    return () => clearInterval(t);
  }, []);

  async function fetchBCR() {
    try {
      const res = await fetch(`${API_BASE}/admin/panel/bcr`);
      if (res.ok) {
        const data = await res.json();
        // Expect: { cities: [{city, code, premiums, claims, lr, suspended, pool_cap_pct}] }
        setCities(data.cities || DEMO_BCR_DATA);
      } else {
        setCities(DEMO_BCR_DATA);
      }
    } catch {
      setCities(DEMO_BCR_DATA);
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
  const totalClaims   = displayCities.reduce((a, c) => a + c.claims, 0);
  const overallLR     = Math.round((totalClaims / totalPremiums) * 100);

  return (
    <section className="bcr-panel">
      {/* Reinsurance activation alert */}
      {reinsAlert && (
        <div className="bcr-reins-alert">
          <span className="bcr-reins-alert__icon">🚨</span>
          <div>
            <strong>Reinsurance Activation Alert</strong>
            <p>One or more cities have crossed 120% of city weekly premium pool cap. Reinsurance treaty review required.</p>
          </div>
        </div>
      )}

      <div className="bcr-panel__header">
        <div>
          <h2 className="bcr-panel__title">BCR / Loss Ratio</h2>
          <p className="bcr-panel__subtitle">
            BCR = claims paid / premiums collected &nbsp;&middot;&nbsp; Target: 0.55-0.70 &nbsp;&middot;&nbsp; Overall: <strong style={{ color: lrColor(overallLR) }}>{overallLR}%</strong>
          </p>
        </div>
        <div className="bcr-legend">
          <span className="bcr-legend__item"><span style={{ background: '#198754' }} />Healthy &lt;70%</span>
          <span className="bcr-legend__item"><span style={{ background: '#ffc107' }} />Watch 70-85%</span>
          <span className="bcr-legend__item"><span style={{ background: '#fd7e14' }} />Suspended &gt;85%</span>
          <span className="bcr-legend__item"><span style={{ background: '#dc3545' }} />Reinsurance &gt;100%</span>
        </div>
      </div>

      <div className="bcr-grid">
        {displayCities.map(c => {
          const bcr = (c.lr / 100).toFixed(2);
          const color = lrColor(c.lr);
          const label = lrLabel(c.lr);
          const isAutoSuspend = c.lr > 85 && overrides[c.code] === undefined;
          const isManuallySuspended = overrides[c.code] === true && c.lr <= 85;
          const isManuallyResumed   = overrides[c.code] === false && c.lr > 85;

          return (
            <div key={c.code} className={`bcr-card ${c.suspended ? 'bcr-card--suspended' : ''}`}>
              <div className="bcr-card__top">
                <div>
                  <p className="bcr-card__city">{c.city}</p>
                  <code className="bcr-card__code">{c.code}</code>
                </div>
                <span className="bcr-card__badge" style={{ background: color + '22', color }}>
                  {label}
                </span>
              </div>

              <div className="bcr-card__numbers">
                <div className="bcr-card__stat">
                  <span>Loss Ratio</span>
                  <strong style={{ color }}>{c.lr}%</strong>
                </div>
                <div className="bcr-card__stat">
                  <span>BCR</span>
                  <strong>{bcr}</strong>
                </div>
                <div className="bcr-card__stat">
                  <span>Pool cap</span>
                  <strong style={{ color: c.pool_cap_pct > 120 ? '#dc3545' : c.pool_cap_pct > 100 ? '#fd7e14' : 'inherit' }}>
                    {c.pool_cap_pct}%
                  </strong>
                </div>
              </div>

              <BCRBar lr={c.lr} />

              <div className="bcr-card__footer">
                <span className="bcr-card__premium">Premiums: Rs.{(c.premiums / 100000).toFixed(1)}L</span>
                <span className="bcr-card__claims">Claims: Rs.{(c.claims / 100000).toFixed(1)}L</span>
              </div>

              {/* Suspension toggle */}
              <div className="bcr-toggle-row">
                <div className="bcr-toggle-info">
                  {isAutoSuspend && <span className="bcr-toggle-auto-tag">Auto-suspended (LR &gt;85%)</span>}
                  {isManuallySuspended && <span className="bcr-toggle-manual-tag">Manually suspended</span>}
                  {isManuallyResumed && <span className="bcr-toggle-override-tag">Warning: Manual override - LR &gt;85%</span>}
                  <span className="bcr-toggle-label">
                    {c.suspended ? 'New enrolments suspended' : 'New enrolments open'}
                  </span>
                </div>
                <button
                  className={`bcr-toggle-btn ${c.suspended ? 'bcr-toggle-btn--resume' : 'bcr-toggle-btn--suspend'}`}
                  onClick={() => toggleSuspension(c.code, c.suspended)}
                >
                  {c.suspended ? 'Resume' : 'Suspend'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
