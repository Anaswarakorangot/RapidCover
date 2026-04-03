// frontend/src/components/admin/RiqiProvenancePanel.jsx
// Dynamic RIQI provenance dashboard — zone-by-zone scores with DB provenance

import React, { useState, useEffect } from 'react';
import { AdminLoader, AdminError, AdminEmpty, ProofCard, SourceBadge } from './AdminProofShared';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const BAND_COLORS = {
  urban_core:   { bg: '#dcfce7', color: '#16a34a' },
  urban_fringe: { bg: '#fef9c3', color: '#ca8a04' },
  periurban:    { bg: '#ffedd5', color: '#ea580c' },
  rural_plus:   { bg: '#fee2e2', color: '#dc2626' },
};

function BandBadge({ band }) {
  const style = BAND_COLORS[band] || { bg: 'var(--gray-bg)', color: 'var(--text-mid)' };
  return (
    <span className="proof-type-badge" style={{ background: style.bg, color: style.color }}>
      {(band || 'unknown').replace(/_/g, ' ')}
    </span>
  );
}

export default function RiqiProvenancePanel() {
  const [data, setData]         = useState(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [seeding, setSeeding]   = useState(false);
  const [recomputing, setRecomputing] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/admin/panel/riqi`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function seedProfiles() {
    setSeeding(true);
    try {
      const res = await fetch(`${API}/admin/panel/riqi/seed`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await load(); // Reload data
    } catch (e) {
      setError(e.message);
    } finally {
      setSeeding(false);
    }
  }

  async function recompute(zoneCode) {
    setRecomputing(zoneCode);
    try {
      const res = await fetch(`${API}/admin/panel/riqi/${zoneCode}/recompute`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await load(); // Reload data
    } catch (e) {
      setError(e.message);
    } finally {
      setRecomputing(null);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <AdminLoader message="Loading RIQI profiles…" />;
  if (error)   return <AdminError message={error} onRetry={load} />;
  if (!data?.zones?.length) return (
    <ProofCard title="📊 RIQI Provenance" subtitle="No zone profiles found">
      <AdminEmpty icon="📊" message="No RIQI profiles. Seed them to get started." />
      <button className="proof-action-btn" onClick={seedProfiles} disabled={seeding}>
        {seeding ? 'Seeding…' : '🌱 Seed RIQI Profiles'}
      </button>
    </ProofCard>
  );

  const zones = data.zones;
  const fromDb = zones.filter(z => z.calculated_from !== 'fallback_city_default').length;
  const fromFallback = zones.length - fromDb;

  return (
    <ProofCard
      title="📊 RIQI Provenance"
      subtitle={`${zones.length} zones — Road Infrastructure Quality Index with data source tracking`}
      source={data.data_source}
      passFail={fromDb > 0 ? 'pass' : 'partial'}
    >
      {/* Summary */}
      <div className="proof-metrics-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">Total Zones</span>
          <span className="proof-metric-card__value">{data.total}</span>
        </div>
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">From Database</span>
          <span className="proof-metric-card__value" style={{ color: 'var(--green-primary)' }}>{fromDb}</span>
        </div>
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">From Fallback</span>
          <span className="proof-metric-card__value" style={{ color: fromFallback > 0 ? 'var(--warning)' : 'var(--text-mid)' }}>{fromFallback}</span>
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <button className="proof-action-btn" onClick={seedProfiles} disabled={seeding}>
          {seeding ? 'Seeding…' : '🌱 Seed Profiles'}
        </button>
        <button className="proof-action-btn proof-action-btn--secondary" onClick={load}>
          🔄 Refresh
        </button>
      </div>

      {/* Zone table */}
      <div className="proof-table-wrapper">
        <table className="proof-table">
          <thead>
            <tr>
              <th>Zone</th>
              <th>City</th>
              <th style={{ textAlign: 'center' }}>RIQI Score</th>
              <th>Band</th>
              <th style={{ textAlign: 'right' }}>Payout ×</th>
              <th style={{ textAlign: 'right' }}>Premium Adj</th>
              <th>Source</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {zones.map(z => {
              const isOpen = expanded === z.zone_code;
              return (
                <React.Fragment key={z.zone_code}>
                  <tr className={isOpen ? 'proof-row--open' : ''}>
                    <td>
                      <span style={{ fontWeight: 800, fontSize: '0.85rem' }}>{z.zone_code}</span>
                      <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-light)' }}>{z.zone_name}</span>
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>{z.city}</td>
                    <td style={{ textAlign: 'center' }}>
                      <div style={{ position: 'relative', display: 'inline-block' }}>
                        <svg width="48" height="48" viewBox="0 0 48 48">
                          <circle cx="24" cy="24" r="20" fill="none" stroke="var(--gray-bg)" strokeWidth="4" />
                          <circle cx="24" cy="24" r="20" fill="none"
                            stroke={z.riqi_score >= 65 ? 'var(--green-primary)' : z.riqi_score >= 45 ? 'var(--warning)' : 'var(--error)'}
                            strokeWidth="4" strokeDasharray={`${(z.riqi_score / 100) * 125.6} 125.6`}
                            strokeLinecap="round" transform="rotate(-90 24 24)" />
                        </svg>
                        <span style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', fontSize: '0.65rem', fontWeight: 900 }}>
                          {z.riqi_score}
                        </span>
                      </div>
                    </td>
                    <td><BandBadge band={z.riqi_band} /></td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>×{z.payout_multiplier}</td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>×{z.premium_adjustment}</td>
                    <td>
                      <span className="proof-source-label" style={{
                        fontSize: '0.65rem', fontWeight: 700, padding: '0.2rem 0.5rem', borderRadius: '6px',
                        background: z.calculated_from === 'fallback_city_default' ? '#fef9c3' : 'var(--green-light)',
                        color: z.calculated_from === 'fallback_city_default' ? 'var(--warning)' : 'var(--green-dark)',
                      }}>
                        {z.calculated_from}
                      </span>
                    </td>
                    <td style={{ display: 'flex', gap: '0.3rem' }}>
                      <button className="proof-expand-btn" onClick={() => setExpanded(isOpen ? null : z.zone_code)}
                        style={{ transform: isOpen ? 'rotate(180deg)' : 'none' }}>▼</button>
                      <button className="proof-expand-btn" onClick={() => recompute(z.zone_code)}
                        disabled={recomputing === z.zone_code} title="Recompute RIQI">
                        {recomputing === z.zone_code ? '⏳' : '🔄'}
                      </button>
                    </td>
                  </tr>
                  {isOpen && (
                    <tr className="proof-detail-row">
                      <td colSpan={8}>
                        <div className="proof-detail-card">
                          <p className="proof-detail-section-label">INPUT METRICS</p>
                          <div className="proof-formula-grid">
                            {z.input_metrics && Object.entries(z.input_metrics).map(([k, v]) => (
                              <div key={k} className="proof-formula-step">
                                <span className="proof-formula-step__label">{k.replace(/_/g, ' ')}</span>
                                <code className="proof-formula-step__value">{v}</code>
                              </div>
                            ))}
                          </div>
                          {z.last_updated_at && (
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-light)', marginTop: '0.75rem' }}>
                              Last updated: {new Date(z.last_updated_at).toLocaleString('en-IN')}
                            </p>
                          )}
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
    </ProofCard>
  );
}
