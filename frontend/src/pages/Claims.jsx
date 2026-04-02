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
          {claim.upi_ref ? ` · UPI: ${claim.upi_ref}` : ''}
        </p>
      </div>
      <button className="pb-close" onClick={onDismiss}>×</button>
    </div>
  );
}

function ClaimCard({ claim }) {
  const style = STATUS_STYLES[claim.status] || STATUS_STYLES.pending;
  const date = claim.created_at
    ? new Date(claim.created_at).toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
    }) : '—';
  const paidDate = claim.paid_at
    ? new Date(claim.paid_at).toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
    }) : null;

  return (
    <div className="claims-card">
      <div className="claim-row">
        <div>
          <p className="claim-amt">₹{claim.amount}</p>
          <p className="claim-date">{date}</p>
        </div>
        <span className={`claim-badge ${style.class}`}>
          {style.icon} {style.label}
        </span>
      </div>
      {(claim.upi_ref || paidDate || claim.fraud_score > 0.5) && (
        <div className="claim-footer">
          {claim.upi_ref && <p className="claim-ref">UPI Ref: {claim.upi_ref}</p>}
          {paidDate && <p className="claim-date">Paid on: {paidDate}</p>}
          {claim.fraud_score != null && claim.fraud_score > 0.5 && (
            <p className="claim-fraud">⚠️ Under review (score: {claim.fraud_score.toFixed(2)})</p>
          )}
        </div>
      )}
    </div>
  );
}

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
              <p className="summary-val text-green-dark" style={{color: 'var(--green-dark)'}}>{summary.paid ?? 0}</p>
              <p className="summary-lbl">Paid</p>
            </div>
            <div className="summary-card">
              <p className="summary-val text-orange-500" style={{color: '#d97706'}}>{summary.pending ?? 0}</p>
              <p className="summary-lbl">Pending</p>
            </div>
            <div className="summary-card">
              <p className="summary-val">{summary.total ?? 0}</p>
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
            <p className="empty-icon">📭</p>
            <p className="empty-title">No claims yet</p>
            <p className="empty-sub">Claims appear here when a trigger fires in your zone.</p>
          </div>
        ) : (
          <div>
            {claims.map(claim => (
              <ClaimCard key={claim.id} claim={claim} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}