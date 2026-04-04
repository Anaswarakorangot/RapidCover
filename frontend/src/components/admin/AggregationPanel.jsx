/**
 * AggregationPanel.jsx — Multi-Trigger Resolver Admin Panel
 *
 * Shows aggregation statistics: how many claims combined multiple triggers,
 * total savings from preventing duplicate payouts, and per-claim aggregation details.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  getAggregationStats,
  getClaimAggregation,
  getAdminClaims,
} from '../../services/adminApi';

/* ─── Trigger type config ────────────────────────────────────────────────── */
const TRIGGER_CFG = {
  rain:     { icon: '🌧️', color: '#3b82f6', label: 'Rain' },
  heat:     { icon: '🌡️', color: '#ef4444', label: 'Heat' },
  aqi:      { icon: '💨', color: '#f97316', label: 'AQI' },
  shutdown: { icon: '🚫', color: '#6b7280', label: 'Shutdown' },
  closure:  { icon: '🏪', color: '#7c3aed', label: 'Closure' },
};

function TriggerTypeBadge({ type }) {
  const cfg = TRIGGER_CFG[type] || { icon: '•', color: '#6b7280', label: type };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 3,
      background: `${cfg.color}15`, color: cfg.color,
      border: `1.5px solid ${cfg.color}30`,
      fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 8,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  );
}

/* ─── Aggregation Detail Viewer ──────────────────────────────────────────── */
function AggregationDetail({ claimId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const result = await getClaimAggregation(claimId);
        setData(result);
      } catch (err) {
        setError(err.message);
      }
      setLoading(false);
    })();
  }, [claimId]);

  if (loading) return (
    <div className="proof-detail-card" style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-light)' }}>
      Loading aggregation data...
    </div>
  );

  if (error || !data) return (
    <div className="proof-detail-card" style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-light)' }}>
      {error || 'No aggregation data for this claim'}
    </div>
  );

  return (
    <div className="proof-detail-card" style={{ marginTop: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div className="proof-detail-section-label" style={{ margin: 0 }}>
          Aggregation Details — Group {data.group_id}
        </div>
        <button className="proof-expand-btn" onClick={onClose}>✕ Close</button>
      </div>

      {/* Aggregation status */}
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        background: data.is_aggregated ? '#dbeafe' : '#f3f4f6',
        color: data.is_aggregated ? '#1e40af' : '#6b7280',
        padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 700, marginBottom: '1rem',
      }}>
        {data.is_aggregated ? '🔗 Multi-Trigger Aggregated' : '• Single Trigger'}
      </div>

      {/* Key metrics */}
      <div className="proof-formula-grid" style={{ marginBottom: '1rem' }}>
        <div className="proof-formula-step">
          <span className="proof-formula-step__label">Primary Trigger</span>
          <span className="proof-formula-step__value">#{data.primary_trigger_id}</span>
        </div>
        <div className="proof-formula-step">
          <span className="proof-formula-step__label">Pre-Aggregation</span>
          <span className="proof-formula-step__value">₹{data.pre_aggregation_payout}</span>
        </div>
        <div className="proof-formula-step">
          <span className="proof-formula-step__label">Post-Aggregation</span>
          <span className="proof-formula-step__value" style={{ fontWeight: 900, color: 'var(--green-dark)' }}>
            ₹{data.post_aggregation_payout}
          </span>
        </div>
        <div className="proof-formula-step">
          <span className="proof-formula-step__label">Savings</span>
          <span className="proof-formula-step__value" style={{ color: data.savings > 0 ? 'var(--green-dark)' : 'var(--text-mid)' }}>
            ₹{data.savings}
          </span>
        </div>
        <div className="proof-formula-step">
          <span className="proof-formula-step__label">Window</span>
          <span className="proof-formula-step__value">{data.window_hours}h</span>
        </div>
        {data.uplift_applied && (
          <div className="proof-formula-step" style={{ background: '#fef9c3' }}>
            <span className="proof-formula-step__label">Severe Uplift</span>
            <span className="proof-formula-step__value" style={{ color: 'var(--warning)' }}>
              +{data.uplift_percent}% (₹{data.uplift_amount})
            </span>
          </div>
        )}
      </div>

      {/* Triggers in window */}
      {data.triggers_in_window?.length > 0 && (
        <div>
          <div className="proof-detail-section-label">Triggers in Window</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {data.triggers_in_window.map((t, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '0.5rem 0.75rem', background: 'var(--gray-bg)', borderRadius: 10,
                borderLeft: t.id === data.primary_trigger_id ? '4px solid var(--green-primary)' : '4px solid var(--border)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <TriggerTypeBadge type={t.type} />
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-light)' }}>
                    #{t.id} · Severity {t.severity}
                  </span>
                  {t.id === data.primary_trigger_id && (
                    <span style={{
                      fontSize: 10, fontWeight: 800, color: 'var(--green-dark)',
                      background: 'var(--green-light)', padding: '1px 6px', borderRadius: 6,
                    }}>PRIMARY</span>
                  )}
                </div>
                <span style={{ fontWeight: 800, fontSize: '0.85rem' }}>₹{t.payout}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suppressed triggers */}
      {data.suppressed_triggers?.length > 0 && (
        <div style={{ marginTop: '0.75rem' }}>
          <div className="proof-detail-section-label">Suppressed Triggers</div>
          <div style={{
            padding: '0.5rem 0.75rem', background: '#fef2f2', borderRadius: 10,
            fontSize: '0.8rem', color: '#991b1b',
          }}>
            Trigger IDs {data.suppressed_triggers.join(', ')} were suppressed — highest payout wins strategy applied.
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Main Component
   ═══════════════════════════════════════════════════════════════════════════ */
export default function AggregationPanel() {
  const [stats, setStats] = useState(null);
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedClaim, setExpandedClaim] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, claimsRes] = await Promise.allSettled([
        getAggregationStats(),
        getAdminClaims({ limit: 50 }),
      ]);
      if (statsRes.status === 'fulfilled') setStats(statsRes.value);
      if (claimsRes.status === 'fulfilled') setClaims(claimsRes.value || []);
    } catch { /* graceful fallback */ }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="admin-section">
        <div className="proof-loader">
          <div className="proof-loader__spinner" />
          <span className="proof-loader__text">Loading aggregation data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-section" style={{ animationDelay: '0.2s' }}>
      <div className="admin-section-label">MULTI-TRIGGER RESOLVER</div>

      {/* Stats Overview */}
      {stats && (
        <div className="proof-metrics-grid" style={{ marginBottom: '1.5rem' }}>
          <div className="proof-metric-card" style={{ borderLeft: '4px solid #3b82f6' }}>
            <span className="proof-metric-card__label">Aggregated Claims</span>
            <span className="proof-metric-card__value" style={{ color: '#1e40af' }}>
              {stats.total_aggregated_claims}
            </span>
          </div>
          <div className="proof-metric-card" style={{ borderLeft: '4px solid var(--warning)' }}>
            <span className="proof-metric-card__label">Triggers Suppressed</span>
            <span className="proof-metric-card__value" style={{ color: 'var(--warning)' }}>
              {stats.total_triggers_suppressed}
            </span>
          </div>
          <div className="proof-metric-card" style={{ borderLeft: '4px solid var(--green-primary)' }}>
            <span className="proof-metric-card__label">Cost Savings</span>
            <span className="proof-metric-card__value" style={{ color: 'var(--green-dark)' }}>
              ₹{stats.total_savings}
            </span>
          </div>
        </div>
      )}

      {/* How it works */}
      <div style={{
        padding: '1.25rem', background: 'var(--gray-bg)', borderRadius: 16, marginBottom: '1.5rem',
        fontSize: '0.88rem', color: 'var(--text-mid)', lineHeight: 1.6,
      }}>
        <p style={{ margin: '0 0 0.5rem', fontWeight: 700, color: 'var(--text-dark)' }}>How aggregation works:</p>
        <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
          <li>When multiple triggers fire within a <strong>6-hour window</strong> for the same partner & zone, they are grouped</li>
          <li><strong>Highest payout wins</strong> — only the trigger with the largest payout creates a claim</li>
          <li>If <strong>3+ trigger types</strong> fire simultaneously, a <strong>10% severe disruption uplift</strong> is applied</li>
          <li>Suppressed triggers are tracked, and <strong>cost savings</strong> are calculated</li>
        </ul>
      </div>

      {/* Claims Table with aggregation info */}
      <div className="proof-detail-section-label">Recent Claims — Aggregation View</div>
      {claims.length === 0 ? (
        <div className="proof-empty">
          <span className="proof-empty__icon">📭</span>
          <span className="proof-empty__message">No claims yet</span>
        </div>
      ) : (
        <div className="proof-table-wrapper">
          <table className="proof-table">
            <thead>
              <tr>
                <th>Claim</th>
                <th>Partner</th>
                <th>Trigger</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Aggregation</th>
              </tr>
            </thead>
            <tbody>
              {claims.map(c => (
                <>
                  <tr key={c.id} className={expandedClaim === c.id ? 'proof-row--open' : ''}>
                    <td style={{ fontWeight: 700 }}>#{c.id}</td>
                    <td>{c.partner_name || '—'}</td>
                    <td><TriggerTypeBadge type={c.trigger_type} /></td>
                    <td style={{ fontWeight: 800 }}>₹{c.amount}</td>
                    <td>
                      <span style={{
                        fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 8,
                        background: c.status === 'paid' ? '#dcfce7' : c.status === 'approved' ? '#dbeafe' : c.status === 'rejected' ? '#fee2e2' : '#fef9c3',
                        color: c.status === 'paid' ? '#166534' : c.status === 'approved' ? '#1e40af' : c.status === 'rejected' ? '#991b1b' : '#854d0e',
                      }}>
                        {c.status.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <button
                        className="proof-action-btn proof-action-btn--secondary"
                        style={{ fontSize: '0.72rem', padding: '0.3rem 0.65rem' }}
                        onClick={() => setExpandedClaim(expandedClaim === c.id ? null : c.id)}
                      >
                        {expandedClaim === c.id ? '↙ Close' : '🔗 View'}
                      </button>
                    </td>
                  </tr>
                  {expandedClaim === c.id && (
                    <tr className="proof-detail-row">
                      <td colSpan={6}>
                        <AggregationDetail
                          claimId={c.id}
                          onClose={() => setExpandedClaim(null)}
                        />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Footer */}
      <div className="proof-card__footer">
        Last computed: {stats?.computed_at ? new Date(stats.computed_at).toLocaleString() : '—'}
        {' · '}
        <button
          onClick={loadData}
          style={{ background: 'none', border: 'none', color: 'var(--green-primary)', fontWeight: 700, cursor: 'pointer' }}
        >
          🔄 Refresh
        </button>
      </div>
    </div>
  );
}
