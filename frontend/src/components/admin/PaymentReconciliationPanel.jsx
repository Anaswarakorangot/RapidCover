/**
 * PaymentReconciliationPanel.jsx — Payment State Machine Admin Panel
 *
 * Shows payment processing stats, failed payments queue, and pending reconciliation queue.
 * Allows retry, confirm, reject, and force_paid actions.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  getPaymentStats,
  getPaymentFailures,
  getPendingReconciliation,
  retryPayment,
  reconcilePayment,
  getClaimPaymentState,
} from '../../services/adminApi';

/* ─── Payment status config ──────────────────────────────────────────────── */
const PAY_STATUS = {
  not_started:       { bg: '#f3f4f6', color: '#6b7280', icon: '⏸️', label: 'Not Started' },
  initiated:         { bg: '#dbeafe', color: '#1e40af', icon: '🔄', label: 'Initiated' },
  confirmed:         { bg: '#dcfce7', color: '#166534', icon: '✅', label: 'Confirmed' },
  failed:            { bg: '#fee2e2', color: '#991b1b', icon: '❌', label: 'Failed' },
  reconcile_pending: { bg: '#fef9c3', color: '#854d0e', icon: '⚠️', label: 'Reconcile Pending' },
};

function PayStatusBadge({ status }) {
  const cfg = PAY_STATUS[status] || PAY_STATUS.not_started;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: cfg.bg, color: cfg.color, border: `1.5px solid ${cfg.bg}`,
      fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  );
}

/* ─── State Flow Diagram ─────────────────────────────────────────────────── */
function PaymentStateFlow({ currentStatus }) {
  const states = [
    { key: 'not_started', label: 'Not Started' },
    { key: 'initiated', label: 'Initiated' },
    { key: 'confirmed', label: 'Confirmed' },
  ];
  const failStates = [
    { key: 'failed', label: 'Failed' },
    { key: 'reconcile_pending', label: 'Reconcile' },
  ];

  function getNodeClass(key) {
    if (key === currentStatus) {
      if (key === 'confirmed') return 'proof-state-node proof-state-node--success';
      if (key === 'failed') return 'proof-state-node proof-state-node--danger';
      if (key === 'reconcile_pending') return 'proof-state-node proof-state-node--warn';
      return 'proof-state-node proof-state-node--active';
    }
    return 'proof-state-node';
  }

  return (
    <div className="proof-state-machine">
      <div className="proof-detail-section-label">Payment State Flow</div>
      <div className="proof-state-flow">
        {states.map((s, i) => (
          <span key={s.key}>
            <span className={getNodeClass(s.key)}>{s.label}</span>
            {i < states.length - 1 && <span className="proof-state-arrow"> → </span>}
          </span>
        ))}
      </div>
      <div className="proof-state-flow" style={{ marginTop: '0.5rem' }}>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-light)', marginRight: 4 }}>↳ Failure path:</span>
        {failStates.map((s, i) => (
          <span key={s.key}>
            <span className={getNodeClass(s.key)}>{s.label}</span>
            {i < failStates.length - 1 && <span className="proof-state-arrow"> → </span>}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ─── Reconcile Modal ────────────────────────────────────────────────────── */
function ReconcileModal({ claim, onClose, onSubmit }) {
  const [action, setAction] = useState('confirm');
  const [providerRef, setProviderRef] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      await onSubmit(claim.claim_id, {
        action,
        provider_ref: providerRef || undefined,
        notes: notes || undefined,
      });
      onClose();
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div style={{
        background: 'var(--white)', borderRadius: 20, padding: '2rem', width: '100%', maxWidth: 480,
        border: '1.5px solid var(--border)', boxShadow: '0 8px 30px rgba(0,0,0,0.12)',
      }}>
        <h3 style={{
          fontFamily: "'Nunito', sans-serif", fontWeight: 900, fontSize: '1.2rem',
          color: 'var(--text-dark)', margin: '0 0 1.5rem',
        }}>
          Reconcile Claim #{claim.claim_id}
        </h3>

        <div style={{ marginBottom: '1rem' }}>
          <label className="notif-control-label">Action</label>
          <select className="notif-select" value={action} onChange={e => setAction(e.target.value)}
            style={{ width: '100%' }}>
            <option value="confirm">✅ Confirm — payment was received</option>
            <option value="force_paid">💰 Force Paid — manual bank transfer</option>
            <option value="reject">❌ Reject — cancel this claim</option>
          </select>
        </div>

        {(action === 'confirm' || action === 'force_paid') && (
          <div style={{ marginBottom: '1rem' }}>
            <label className="notif-control-label">Provider Reference</label>
            <input
              type="text"
              className="notif-select"
              style={{ width: '100%' }}
              value={providerRef}
              onChange={e => setProviderRef(e.target.value)}
              placeholder={action === 'confirm' ? 'e.g. UPI20260404143200' : 'auto-generated if empty'}
            />
          </div>
        )}

        <div style={{ marginBottom: '1.5rem' }}>
          <label className="notif-control-label">Notes (optional)</label>
          <textarea
            className="notif-select"
            style={{ width: '100%', minHeight: 60, resize: 'vertical' }}
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Reconciliation notes..."
          />
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <button className="proof-action-btn proof-action-btn--secondary" onClick={onClose}>Cancel</button>
          <button
            className="proof-action-btn"
            onClick={handleSubmit}
            disabled={submitting || (action === 'confirm' && !providerRef)}
            style={action === 'reject' ? { background: 'var(--error)' } : {}}
          >
            {submitting ? 'Processing...' : action === 'confirm' ? 'Confirm Payment' : action === 'reject' ? 'Reject Claim' : 'Force Paid'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Payment Detail Drawer ──────────────────────────────────────────────── */
function PaymentDetailDrawer({ claimId, onClose }) {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await getClaimPaymentState(claimId);
        setState(data);
      } catch { setState(null); }
      setLoading(false);
    })();
  }, [claimId]);

  if (loading) return (
    <div className="proof-detail-card" style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-light)' }}>
      Loading payment state...
    </div>
  );

  if (!state) return (
    <div className="proof-detail-card" style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-light)' }}>
      No payment data available
    </div>
  );

  return (
    <div className="proof-detail-card" style={{ marginTop: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div className="proof-detail-section-label" style={{ margin: 0 }}>Payment State Details</div>
        <button className="proof-expand-btn" onClick={onClose}>✕ Close</button>
      </div>

      <PaymentStateFlow currentStatus={state.current_status} />

      <div className="proof-formula-grid" style={{ marginTop: '1rem' }}>
        <div className="proof-formula-step">
          <span className="proof-formula-step__label">Status</span>
          <span className="proof-formula-step__value">{state.current_status}</span>
        </div>
        <div className="proof-formula-step">
          <span className="proof-formula-step__label">Idempotency Key</span>
          <span className="proof-formula-step__value">{state.idempotency_key || '—'}</span>
        </div>
        <div className="proof-formula-step">
          <span className="proof-formula-step__label">Total Attempts</span>
          <span className="proof-formula-step__value">{state.total_attempts}/{state.max_retries}</span>
        </div>
      </div>

      {state.attempts?.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <div className="proof-detail-section-label">Attempt History</div>
          {state.attempts.map((att, i) => (
            <div key={i} style={{
              padding: '0.6rem 0.75rem', marginBottom: '0.4rem',
              background: 'var(--gray-bg)', borderRadius: 10, fontSize: '0.8rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 4 }}>
                <span style={{ fontWeight: 700, color: 'var(--text-dark)' }}>
                  Attempt #{att.attempt_num}
                </span>
                <span style={{
                  fontWeight: 700, fontSize: 11,
                  color: att.status === 'success' ? '#166534' : att.status === 'failed' ? '#991b1b' : '#1e40af',
                }}>
                  {att.status?.toUpperCase()}
                </span>
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-light)', marginTop: 2 }}>
                Key: {att.idempotency_key} · {att.initiated_at ? new Date(att.initiated_at).toLocaleString() : '—'}
              </div>
              {att.error && (
                <div style={{ fontSize: '0.72rem', color: 'var(--error)', marginTop: 2 }}>
                  Error: {att.error}
                </div>
              )}
              {att.provider_ref && (
                <div style={{ fontSize: '0.72rem', color: '#166534', marginTop: 2 }}>
                  Ref: {att.provider_ref}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {state.reconcile_reason && (
        <div style={{
          marginTop: '0.75rem', padding: '0.6rem 0.75rem',
          background: '#fef9c3', borderRadius: 10, fontSize: '0.8rem', color: '#854d0e',
        }}>
          ⚠️ Escalation reason: {state.reconcile_reason}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Main Component
   ═══════════════════════════════════════════════════════════════════════════ */
export default function PaymentReconciliationPanel() {
  const [stats, setStats] = useState(null);
  const [failures, setFailures] = useState([]);
  const [reconcileQueue, setReconcileQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [expandedClaim, setExpandedClaim] = useState(null);
  const [reconcileTarget, setReconcileTarget] = useState(null);
  const [retryingId, setRetryingId] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, failRes, reconRes] = await Promise.allSettled([
        getPaymentStats(),
        getPaymentFailures(50),
        getPendingReconciliation(50),
      ]);
      if (statsRes.status === 'fulfilled') setStats(statsRes.value);
      if (failRes.status === 'fulfilled') setFailures(failRes.value?.claims || []);
      if (reconRes.status === 'fulfilled') setReconcileQueue(reconRes.value?.claims || []);
    } catch { /* fallback handled */ }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleRetry(claimId) {
    setRetryingId(claimId);
    try {
      await retryPayment(claimId);
      await loadData();
    } catch (err) {
      alert(`Retry failed: ${err.message}`);
    }
    setRetryingId(null);
  }

  async function handleReconcile(claimId, data) {
    await reconcilePayment(claimId, data);
    await loadData();
  }

  if (loading) {
    return (
      <div className="admin-section">
        <div className="proof-loader">
          <div className="proof-loader__spinner" />
          <span className="proof-loader__text">Loading payment data...</span>
        </div>
      </div>
    );
  }

  const TABS = [
    { id: 'overview', label: 'Overview' },
    { id: 'failures', label: `Failed (${failures.length})` },
    { id: 'reconcile', label: `Reconcile (${reconcileQueue.length})` },
  ];

  return (
    <div className="admin-section" style={{ animationDelay: '0.2s' }}>
      <div className="admin-section-label">PAYMENT RECONCILIATION STATE MACHINE</div>

      {/* Stats Overview */}
      {stats && (
        <div className="proof-metrics-grid" style={{ marginBottom: '1.5rem' }}>
          <div className="proof-metric-card" style={{ borderLeft: '4px solid #3b82f6' }}>
            <span className="proof-metric-card__label">Initiated</span>
            <span className="proof-metric-card__value" style={{ color: '#1e40af' }}>{stats.initiated}</span>
          </div>
          <div className="proof-metric-card" style={{ borderLeft: '4px solid var(--green-primary)' }}>
            <span className="proof-metric-card__label">Confirmed</span>
            <span className="proof-metric-card__value" style={{ color: 'var(--green-dark)' }}>{stats.confirmed}</span>
          </div>
          <div className="proof-metric-card" style={{ borderLeft: '4px solid var(--error)' }}>
            <span className="proof-metric-card__label">Failed</span>
            <span className="proof-metric-card__value" style={{ color: 'var(--error)' }}>{stats.failed}</span>
          </div>
          <div className="proof-metric-card" style={{ borderLeft: '4px solid var(--warning)' }}>
            <span className="proof-metric-card__label">Pending Reconciliation</span>
            <span className="proof-metric-card__value" style={{ color: 'var(--warning)' }}>{stats.reconcile_pending}</span>
          </div>
        </div>
      )}

      {/* State Flow Reference */}
      <PaymentStateFlow currentStatus={null} />

      {/* Sub-tabs */}
      <div style={{
        display: 'flex', gap: '0.5rem', margin: '1.5rem 0 1rem',
        background: 'rgba(226,236,226,0.4)', padding: '0.3rem', borderRadius: 12, width: 'fit-content',
      }}>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`admin-tab ${activeTab === t.id ? 'admin-tab--active' : ''}`}
            onClick={() => setActiveTab(t.id)}
            style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div>
          <div style={{
            padding: '1.25rem', background: 'var(--gray-bg)', borderRadius: 16,
            fontSize: '0.88rem', color: 'var(--text-mid)', lineHeight: 1.6,
          }}>
            <p style={{ margin: '0 0 0.5rem', fontWeight: 700, color: 'var(--text-dark)' }}>How it works:</p>
            <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
              <li>Each approved claim goes through: <strong>Not Started → Initiated → Confirmed</strong></li>
              <li>If payment fails, it can be <strong>retried up to 3 times</strong></li>
              <li>After 2+ failures, it's <strong>auto-escalated to reconciliation</strong></li>
              <li>Admin can <strong>confirm, reject, or force-pay</strong> reconciliation items</li>
              <li>Each attempt uses an <strong>idempotency key</strong> (RC-CLM-{'{id}'}-ATT-{'{n}'})</li>
            </ul>
          </div>
        </div>
      )}

      {/* Failed Payments Tab */}
      {activeTab === 'failures' && (
        <div>
          {failures.length === 0 ? (
            <div className="proof-empty">
              <span className="proof-empty__icon">✅</span>
              <span className="proof-empty__message">No failed payments</span>
            </div>
          ) : (
            <div className="proof-table-wrapper">
              <table className="proof-table">
                <thead>
                  <tr>
                    <th>Claim</th>
                    <th>Partner</th>
                    <th>Amount</th>
                    <th>Attempts</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {failures.map(f => (
                    <>
                      <tr key={f.claim_id} className={expandedClaim === f.claim_id ? 'proof-row--open' : ''}>
                        <td style={{ fontWeight: 700 }}>#{f.claim_id}</td>
                        <td>{f.partner_name || '—'}</td>
                        <td style={{ fontWeight: 800 }}>₹{f.amount}</td>
                        <td>{f.payment_state?.total_attempts || 0}/{f.payment_state?.max_retries || 3}</td>
                        <td><PayStatusBadge status={f.payment_state?.current_status} /></td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                            <button
                              className="proof-action-btn"
                              style={{ fontSize: '0.72rem', padding: '0.35rem 0.75rem' }}
                              onClick={() => handleRetry(f.claim_id)}
                              disabled={retryingId === f.claim_id}
                            >
                              {retryingId === f.claim_id ? '...' : '🔄 Retry'}
                            </button>
                            <button
                              className="proof-action-btn proof-action-btn--secondary"
                              style={{ fontSize: '0.72rem', padding: '0.35rem 0.75rem' }}
                              onClick={() => setExpandedClaim(expandedClaim === f.claim_id ? null : f.claim_id)}
                            >
                              {expandedClaim === f.claim_id ? '↙ Close' : '↗ Details'}
                            </button>
                          </div>
                        </td>
                      </tr>
                      {expandedClaim === f.claim_id && (
                        <tr className="proof-detail-row">
                          <td colSpan={6}>
                            <PaymentDetailDrawer
                              claimId={f.claim_id}
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
        </div>
      )}

      {/* Reconciliation Queue Tab */}
      {activeTab === 'reconcile' && (
        <div>
          {reconcileQueue.length === 0 ? (
            <div className="proof-empty">
              <span className="proof-empty__icon">✅</span>
              <span className="proof-empty__message">No claims pending reconciliation</span>
            </div>
          ) : (
            <div className="proof-table-wrapper">
              <table className="proof-table">
                <thead>
                  <tr>
                    <th>Claim</th>
                    <th>Partner</th>
                    <th>Amount</th>
                    <th>Reason</th>
                    <th>Escalated</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {reconcileQueue.map(r => (
                    <>
                      <tr key={r.claim_id} className={expandedClaim === r.claim_id ? 'proof-row--open' : ''}>
                        <td style={{ fontWeight: 700 }}>#{r.claim_id}</td>
                        <td>{r.partner_name || '—'}</td>
                        <td style={{ fontWeight: 800 }}>₹{r.amount}</td>
                        <td style={{ fontSize: '0.78rem', color: 'var(--warning)' }}>
                          {r.reconcile_reason || 'Manual escalation'}
                        </td>
                        <td style={{ fontSize: '0.78rem', color: 'var(--text-light)' }}>
                          {r.escalated_at ? new Date(r.escalated_at).toLocaleString() : '—'}
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                            <button
                              className="proof-action-btn"
                              style={{ fontSize: '0.72rem', padding: '0.35rem 0.75rem' }}
                              onClick={() => setReconcileTarget(r)}
                            >
                              ⚙️ Reconcile
                            </button>
                            <button
                              className="proof-action-btn proof-action-btn--secondary"
                              style={{ fontSize: '0.72rem', padding: '0.35rem 0.75rem' }}
                              onClick={() => setExpandedClaim(expandedClaim === r.claim_id ? null : r.claim_id)}
                            >
                              {expandedClaim === r.claim_id ? '↙ Close' : '↗ Details'}
                            </button>
                          </div>
                        </td>
                      </tr>
                      {expandedClaim === r.claim_id && (
                        <tr className="proof-detail-row">
                          <td colSpan={6}>
                            <PaymentDetailDrawer
                              claimId={r.claim_id}
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
        </div>
      )}

      {/* Reconcile Modal */}
      {reconcileTarget && (
        <ReconcileModal
          claim={reconcileTarget}
          onClose={() => setReconcileTarget(null)}
          onSubmit={handleReconcile}
        />
      )}

      {/* Footer */}
      <div className="proof-card__footer">
        Last refreshed: {stats?.computed_at ? new Date(stats.computed_at).toLocaleString() : '—'}
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
