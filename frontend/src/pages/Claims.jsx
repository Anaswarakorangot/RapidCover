/**
 * Claims.jsx  –  Partner claims list
 *
 * Person 1 Phase 2:
 *   - Shows payout banner when a new paid claim arrives
 *   - Fetches claims, claims summary
 *   - Now themed with the green design system!
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';

/* ── Inline trigger evidence component ── */
function InlineTriggerEvidence({ zoneId }) {
  const [ev, setEv] = useState(null);
  useEffect(() => {
    if (!zoneId) return;
    api.getZoneTriggerEvidence(zoneId).then(setEv).catch(() => {});
  }, [zoneId]);

  if (!ev || !ev.recent_non_triggers?.length) return null;

  const latest = ev.recent_non_triggers[0];
  const pct = Math.min((latest.measured_value / latest.threshold) * 100, 100);
  const exceedsThreshold = pct >= 100;

  return (
    <div className="ite-wrap">
      <div className="ite-header">
        <span className="ite-title">⚡ Trigger Evidence</span>
        {ev.consensus_score !== undefined && (
          <span className="ite-consensus-row">
            <span style={{ fontSize: 9, background: '#dcfce7', padding: '1px 6px', borderRadius: 10, fontWeight: 700 }}>
              Consensus {(ev.consensus_score * 100).toFixed(0)}%
            </span>
          </span>
        )}
      </div>
      <div className="ite-metric-row">
        <span className="ite-metric-key">{latest.condition_type} measured</span>
        <span className="ite-metric-val" style={{ color: exceedsThreshold ? '#dc2626' : '#166534' }}>
          {latest.measured_value} {exceedsThreshold ? '⬆ above threshold' : ''}
        </span>
      </div>
      <div className="ite-bar-bg">
        <div className="ite-bar-fill" style={{ width: `${pct}%`, background: exceedsThreshold ? '#dc2626' : '#22c55e' }} />
      </div>
      <div className="ite-metric-row" style={{ marginTop: 2 }}>
        <span className="ite-metric-key">Payout threshold</span>
        <span className="ite-metric-val">{latest.threshold}</span>
      </div>
      <p className="ite-source">
        ✅ Verified by multi-source data · Auto-processed
      </p>
    </div>
  );
}
import ProofCard from '../components/ProofCard';

const POLL_INTERVAL_MS = 5_000;
const POLL_TIMEOUT_MS = 120_000;

const S = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=DM+Sans:wght@400;500;600&display=swap');

  :root {
    --green-primary: #3DB85C;
    --green-dark:    #2a9e47;
    --green-light:   #e8f7ed;
    --text-dark:     #1a2e1a;
    --text-mid:      #4a5e4a;
    --text-light:    #8a9e8a;
    --white:         #ffffff;
    --gray-bg:       #f7f9f7;
    --border:        #e2ece2;
    --warning:       #d97706;
    --error:         #dc2626;
  }

  .claims-wrap {
    font-family: 'DM Sans', sans-serif;
    color: var(--text-dark);
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 24px 16px 32px;
    background: var(--gray-bg);
    min-height: 100vh;
  }

  .claims-page-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 24px;
    color: var(--text-dark);
  }
  .claims-page-sub { font-size: 13px; color: var(--text-light); margin-top: 2px; }

  .claims-card {
    background: var(--white);
    border-radius: 20px;
    border: 1.5px solid var(--border);
    padding: 16px 18px;
    margin-bottom: 12px;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 20px;
  }
  .summary-card {
    background: var(--white);
    border: 1.5px solid var(--border);
    border-radius: 16px;
    padding: 12px;
    text-align: center;
  }
  .summary-val { font-family: 'Nunito', sans-serif; font-size: 20px; font-weight: 900; }
  .summary-lbl { font-size: 11px; color: var(--text-mid); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }

  .claim-row {
    display: flex; justify-content: space-between; align-items: flex-start;
  }
  .claim-amt { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 18px; color: var(--text-dark); }
  .claim-date { font-size: 12px; color: var(--text-light); margin-top: 2px; }
  .claim-badge { 
    font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 12px; 
    display: inline-flex; align-items: center; gap: 4px; border: 1.5px solid transparent;
  }
  .badge-paid { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
  .badge-approved { background: #dbeafe; color: #1e40af; border-color: #bfdbfe; }
  .badge-pending { background: #fffbeb; color: #b45309; border-color: #fde68a; }
  .badge-rejected { background: #fef2f2; color: #991b1b; border-color: #fecaca; }

  .claim-footer { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--border); }
  .claim-ref { font-size: 11.5px; color: var(--green-dark); font-weight: 600; }
  .claim-fraud { font-size: 11.5px; color: #b45309; font-weight: 600; }

  .payout-banner {
    position: relative; background: var(--green-primary); color: white;
    border-radius: 20px; padding: 16px; margin-bottom: 16px;
    display: flex; gap: 12px; align-items: flex-start;
  }
  .payout-icon { font-size: 28px; }
  .pb-title { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 16px; margin-bottom: 2px; }
  .pb-sub { font-size: 12.5px; opacity: 0.9; }
  .pb-close {
    position: absolute; top: 12px; right: 14px;
    background: transparent; border: none; color: white;
    font-size: 20px; opacity: 0.8; cursor: pointer;
  }

  .empty-state { text-align: center; padding: 40px 20px; }
  .empty-icon { font-size: 48px; margin-bottom: 12px; }
  .empty-title { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 18px; color: var(--text-dark); }
  .empty-sub { font-size: 13px; color: var(--text-mid); margin-top: 4px; }

  /* ── Inline trigger evidence ── */
  .ite-wrap {
    background: #f0fdf4;
    border: 1.5px solid #bbf7d0;
    border-radius: 14px;
    padding: 12px 14px;
    margin-top: 8px;
    animation: evidenceFade 0.35s ease;
  }
  @keyframes evidenceFade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
  .ite-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
  .ite-title { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 13px; color: #166534; display: flex; align-items: center; gap: 5px; }
  .ite-metric-row { display: flex; justify-content: space-between; align-items: center; font-size: 12px; margin-bottom: 5px; }
  .ite-metric-key { color: var(--text-mid); }
  .ite-metric-val { font-weight: 700; color: var(--text-dark); }
  .ite-bar-bg { height: 5px; background: #d1fae5; border-radius: 10px; overflow: hidden; margin: 4px 0 2px; }
  .ite-bar-fill { height: 100%; border-radius: 10px; transition: width 0.5s ease; }
  .ite-source { font-size: 10px; color: var(--text-light); text-align: right; margin-top: 6px; }
  .ite-consensus-row { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #166534; margin-top: 4px; }
`;

const STATUS_STYLES = {
  paid: { class: 'badge-paid', label: 'PAID', icon: '✅' },
  approved: { class: 'badge-approved', label: 'APPROVED', icon: '👍' },
  pending: { class: 'badge-pending', label: 'PENDING', icon: '⏳' },
  rejected: { class: 'badge-rejected', label: 'REJECTED', icon: '❌' },
};

function PayoutBanner({ claim, onDismiss }) {
  if (!claim) return null;
  return (
    <div className="payout-banner">
      <span className="payout-icon">💸</span>
      <div>
        <p className="pb-title">Payout received!</p>
        <p className="pb-sub">
          ₹{claim.amount} · Claim #{claim.id}
          {claim.upi_ref ? (claim.upi_ref.startsWith('tr_') ? ` · Stripe: ${claim.upi_ref}` : ` · UPI: ${claim.upi_ref}`) : ''}
        </p>
      </div>
      <button className="pb-close" onClick={onDismiss}>×</button>
    </div>
  );
}

// Replaced local ClaimCard with B2 ProofCard.

export default function Claims() {
  const [claims, setClaims] = useState([]);
  const [summary, setSummary] = useState(null);
  const [newPaidClaim, setNewPaidClaim] = useState(null);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pollingActive, setPollingActive] = useState(true);

  const pollRef = useRef(null);
  const activityRef = useRef(null);
  const seenPaidIdsRef = useRef(new Set());

  const fetchAll = useCallback(async (isInitial = false) => {
    try {
      const [claimsRes, summaryRes, triggersRes] = await Promise.allSettled([
        api.getClaims({ limit: 20 }),
        api.getClaimsSummary(),
        api.getActiveTriggers().catch(() => []),
      ]);

      if (claimsRes.status === 'fulfilled') {
        const list = Array.isArray(claimsRes.value) ? claimsRes.value : (claimsRes.value?.claims || []);
        setClaims(list);

        const paidNow = list.find(
          c => c.status === 'paid' && !seenPaidIdsRef.current.has(c.id)
        );
        if (paidNow) {
          seenPaidIdsRef.current.add(paidNow.id);
          setNewPaidClaim(paidNow);
          setBannerDismissed(false);
          resetActivityTimer();
        }
      }

      if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value);

      if (triggersRes.status === 'fulfilled') {
        const triggers = Array.isArray(triggersRes.value) ? triggersRes.value : (triggersRes.value?.triggers || []);
        if (triggers.length > 0) resetActivityTimer();
      }

      if (isInitial) setError(null);
    } catch (err) {
      if (isInitial) setError(err.message);
    } finally {
      if (isInitial) setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const resetActivityTimer = useCallback(() => {
    if (activityRef.current) clearTimeout(activityRef.current);
    setPollingActive(true);
    activityRef.current = setTimeout(() => setPollingActive(false), POLL_TIMEOUT_MS);
  }, []);

  useEffect(() => {
    fetchAll(true);
    resetActivityTimer();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (activityRef.current) clearTimeout(activityRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (pollingActive) {
      pollRef.current = setInterval(() => fetchAll(false), POLL_INTERVAL_MS);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [pollingActive, fetchAll]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--gray-bg)' }}>
        <div style={{ width: 32, height: 32, border: '3px solid var(--green-light)', borderTopColor: 'var(--green-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      </div>
    );
  }

  return (
    <>
      <style>{S}</style>
      <div className="claims-wrap">
        <div>
          <h1 className="claims-page-title">Claims</h1>
          <p className="claims-page-sub">
            {pollingActive ? '🔄 Auto-updating' : 'Your automatic payouts'}
          </p>
        </div>

        {!bannerDismissed && (
          <PayoutBanner claim={newPaidClaim} onDismiss={() => setBannerDismissed(true)} />
        )}

        {summary && (
          <div className="summary-grid">
            <div className="summary-card">
              <p className="summary-val text-green-dark" style={{ color: 'var(--green-dark)' }}>
                {/* Count of paid claims = total_claims - pending_claims */}
                {(summary.total_claims ?? 0) - (summary.pending_claims ?? 0)}
              </p>
              <p className="summary-lbl">Paid</p>
            </div>
            <div className="summary-card">
              <p className="summary-val text-orange-500" style={{ color: '#d97706' }}>{summary.pending_claims ?? 0}</p>
              <p className="summary-lbl">Pending</p>
            </div>
            <div className="summary-card">
              <p className="summary-val">{summary.total_claims ?? 0}</p>
              <p className="summary-lbl">Total</p>
            </div>
          </div>
        )}

        {error && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '12px', borderRadius: '12px', color: '#991b1b', fontSize: 13, marginBottom: 16 }}>
            {error}
          </div>
        )}

        {claims.length === 0 ? (
          <div className="empty-state">
            <p className="empty-icon">💭</p>
            <p className="empty-title">No claims yet</p>
            <p className="empty-sub">Claims appear here when a trigger fires in your zone.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {claims.map(claim => (
              <div key={claim.id}>
                <ProofCard
                  triggerType={claim.trigger_type}
                  severity={claim.severity}
                  status={claim.status}
                  amount={claim.amount}
                  upiRef={claim.upi_ref}
                  createdAt={claim.created_at}
                  paidAt={claim.paid_at}
                  fraudScore={claim.fraud_score}
                  claimId={claim.id}
                  validationData={claim.validation_data}
                  disruptionCategory={claim.disruption_category}
                  disruptionFactor={claim.disruption_factor}
                  paymentStatus={claim.payment_status}
                />
                {(claim.status === 'paid' || claim.status === 'approved') && claim.zone_id && (
                  <InlineTriggerEvidence zoneId={claim.zone_id} />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}