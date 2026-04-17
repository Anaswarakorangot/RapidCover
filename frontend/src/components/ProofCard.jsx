/**
 * ProofCard.jsx  –  Reusable proof / timestamp card
 *
 * Person 3 Upgrades:
 *   - Now expandable to show "Claim Explanation" details
 *   - Shows exact metrics (e.g. 87mm/hr) and calculation breakdown
 *   - Professional icon-free UI
 *
 * B2 shared component. Used in Claims list, partner Dashboard, and demo proofs.
 *
 * Props:
 *   triggerType        {string}       'rain' | 'heat' | 'aqi' | 'shutdown' | 'closure'
 *   severity           {number?}      1–5, shown via SourceBadge
 *   status             {string}       'paid' | 'approved' | 'pending' | 'rejected'
 *   amount             {number?}      payout amount in ₹
 *   upiRef             {string?}      UPI reference (shown only for paid)
 *   createdAt          {string?}      ISO timestamp of claim / trigger creation
 *   paidAt             {string?}      ISO timestamp of payout
 *   metricValue        {string?}      Optional measurement label e.g. "87mm/hr", "AQI 410"
 *   fraudScore         {number?}      0.0–1.0 fraud score (shows warning if > 0.5)
 *   claimId            {number?}      Claim ID for reference
 *   validationData     {object|string?} Detailed validation and metric logic
 *   disruptionCategory {string?}      'full_halt' | 'severe_reduction' | 'moderate_reduction' | 'minor_reduction'
 *   disruptionFactor   {number?}      0.0–1.0 payout factor
 *   paymentStatus      {string?}      'not_started' | 'initiated' | 'confirmed' | 'failed' | 'reconcile_pending'
 */

import { useState, useEffect } from 'react';
import SourceBadge from './SourceBadge';
import api from '../services/api';

/* ─── Status config ──────────────────────────────────────────────────────── */
const STATUS_CFG = {
  paid:     { bg: '#dcfce7', color: '#166534', border: '#bbf7d0', label: 'PAID' },
  approved: { bg: '#dbeafe', color: '#1e40af', border: '#bfdbfe', label: 'APPROVED' },
  pending:  { bg: '#fef9c3', color: '#854d0e', border: '#fde68a', label: 'PENDING' },
  rejected: { bg: '#fee2e2', color: '#991b1b', border: '#fecaca', label: 'REJECTED' },
};

const FALLBACK_STATUS = { bg: '#f3f4f6', color: '#374151', border: '#e5e7eb', label: 'UNKNOWN' };

/* ─── Disruption category config ─────────────────────────────────────────── */
const DISRUPTION_CFG = {
  full_halt:          { icon: '🛑', label: 'Full Halt',          color: '#ef4444', bg: '#fee2e2' },
  severe_reduction:   { icon: '⚠️', label: 'Severe Reduction',   color: '#f97316', bg: '#ffedd5' },
  moderate_reduction: { icon: '📉', label: 'Moderate Reduction', color: '#eab308', bg: '#fef9c3' },
  minor_reduction:    { icon: '📊', label: 'Minor Reduction',    color: '#3b82f6', bg: '#dbeafe' },
};

/* ─── Payment status config ──────────────────────────────────────────────── */
const PAY_CFG = {
  not_started:       { icon: '⏸️', label: 'Not started',      color: '#6b7280' },
  initiated:         { icon: '🔄', label: 'Processing',        color: '#1e40af' },
  confirmed:         { icon: '✅', label: 'Payment confirmed', color: '#166534' },
  failed:            { icon: '❌', label: 'Payment failed',    color: '#991b1b' },
  reconcile_pending: { icon: '⚠️', label: 'Under review',     color: '#854d0e' },
};

/* ─── Date helpers ───────────────────────────────────────────────────────── */
function fmtDate(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function fmtShort(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

/* ─── Consensus Meter ─────────────────────────────────────────────────────── */
function ConsensusMeter({ explanation }) {
  // Calculate current timestamp once on mount
  const [now] = useState(() => Date.now());

  if (!explanation) return null;

  // Calculate consensus score based on available evidence
  const checks = [
    { label: 'Multi-source', pass: explanation.data_sources && explanation.data_sources.length >= 2 },
    { label: 'Zone match', pass: explanation.zone_match },
    { label: 'Live data', pass: explanation.source_mode === 'live' },
    { label: 'Fresh', pass: explanation.trigger_started_at &&
      (now - new Date(explanation.trigger_started_at).getTime()) < 3600000 }, // < 1 hour
  ];

  const passedChecks = checks.filter(c => c.pass).length;
  const consensusPercent = Math.round((passedChecks / checks.length) * 100);
  const barColor = consensusPercent >= 75 ? '#2a9e47' : consensusPercent >= 50 ? '#f97316' : '#dc2626';

  return (
    <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 12, padding: 12 }}>
      <p style={{ fontSize: 11, fontWeight: 700, color: '#166534', marginBottom: 8, textTransform: 'uppercase' }}>
        Data Consensus Score
      </p>

      {/* Consensus bar */}
      <div style={{ background: '#e5e7eb', borderRadius: 8, height: 8, marginBottom: 10, overflow: 'hidden' }}>
        <div style={{
          background: barColor,
          height: '100%',
          width: `${consensusPercent}%`,
          transition: 'width 0.3s ease'
        }} />
      </div>

      {/* Check list */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 11 }}>
        {checks.map((check, idx) => (
          <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ fontSize: 14 }}>{check.pass ? '✅' : '⚠️'}</span>
            <span style={{ color: check.pass ? '#166534' : '#6b7280' }}>{check.label}</span>
          </div>
        ))}
      </div>

      {/* Sources */}
      {explanation.data_sources && explanation.data_sources.length > 0 && (
        <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #dcfce7' }}>
          <p style={{ fontSize: 10, color: '#4a5e4a', marginBottom: 4 }}>Data Sources:</p>
          <p style={{ fontSize: 11, fontWeight: 600, color: '#166534' }}>
            {explanation.data_sources.join(' • ')}
          </p>
        </div>
      )}
    </div>
  );
}

/* ─── Component ──────────────────────────────────────────────────────────── */
export default function ProofCard({
  triggerType,
  severity,
  status = 'pending',
  amount,
  upiRef,
  createdAt,
  paidAt,
  metricValue,
  fraudScore,
  claimId,
  validationData,
  disruptionCategory,
  disruptionFactor,
  paymentStatus,
}) {
  const [expanded, setExpanded] = useState(false);
  const [explanation, setExplanation] = useState(null);
  const [loadingExpl, setLoadingExpl] = useState(false);
  const stCfg = STATUS_CFG[status] || FALLBACK_STATUS;
  const dCfg = disruptionCategory ? DISRUPTION_CFG[disruptionCategory] : null;
  const pCfg = paymentStatus ? PAY_CFG[paymentStatus] : null;

  useEffect(() => {
    if (expanded && !explanation && claimId) {
      setLoadingExpl(true); // eslint-disable-line react-hooks/set-state-in-effect
      api.getClaimExplanation(claimId)
        .then(setExplanation)
        .catch(err => console.error("Failed to fetch explanation:", err))
        .finally(() => setLoadingExpl(false));
    }
  }, [expanded, explanation, claimId]);

  // Attempt to parse validation data for the deep dive
  let trLog = null;
  if (validationData) {
    try {
      const parsed = typeof validationData === 'string' ? JSON.parse(validationData) : validationData;
      trLog = parsed.transaction_log || parsed;
    } catch (_e) {
      console.warn("Failed to parse claim validation data", _e);
    }
  }

  const cityCap = trLog?.city_cap_check;
  const triggerDetail = trLog?.trigger || {};

  return (
    <div
      onClick={() => setExpanded(!expanded)}
      style={{
        background: '#ffffff',
        border: '1.5px solid #e2ece2',
        borderRadius: 18,
        overflow: 'hidden',
        fontFamily: "'DM Sans', sans-serif",
        cursor: 'pointer',
        transition: 'transform 0.1s, box-shadow 0.2s',
        transform: expanded ? 'scale(1.01)' : 'scale(1)',
        boxShadow: expanded ? '0 8px 24px rgba(61, 184, 92, 0.1)' : 'none',
      }}
    >
      {/* Header strip */}
      <div
        style={{
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #e2ece2',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <SourceBadge type={triggerType} severity={severity} size="md" />
          {(metricValue || triggerDetail.severity_label) && (
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                background: '#f3f4f6',
                color: '#374151',
                padding: '2px 8px',
                borderRadius: 20,
              }}
            >
              {metricValue || triggerDetail.severity_label}
            </span>
          )}
          {/* Disruption category badge */}
          {dCfg && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 3,
                background: dCfg.bg,
                color: dCfg.color,
                fontSize: 10,
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 20,
              }}
            >
              {dCfg.icon} {dCfg.label}
              {disruptionFactor != null && ` · ${(disruptionFactor * 100).toFixed(0)}%`}
            </span>
          )}
        </div>

        {/* Status chip */}
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            background: stCfg.bg,
            color: stCfg.color,
            border: `1.5px solid ${stCfg.border}`,
            fontSize: 11,
            fontWeight: 700,
            padding: '3px 10px',
            borderRadius: 20,
            whiteSpace: 'nowrap',
          }}
        >
          {stCfg.label}
        </span>
      </div>

      {/* Body */}
      <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {/* Amount */}
        {amount != null && (
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
            <span style={{
              fontFamily: "'Nunito', sans-serif",
              fontWeight: 900,
              fontSize: 22,
              color: status === 'paid' ? '#2a9e47' : '#1a2e1a',
            }}>
              Rs.{amount}
            </span>
            {claimId && (
              <span style={{ fontSize: 11, color: '#8a9e8a' }}>- Claim #{claimId}</span>
            )}
          </div>
        )}

        {/* Timestamps */}
        {createdAt && !expanded && (
          <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>
             {fmtDate(createdAt)}
          </p>
        )}
        {paidAt && !expanded && (
          <p style={{ fontSize: 12, color: '#2a9e47', fontWeight: 600, margin: 0 }}>
            Paid {fmtShort(paidAt)}
          </p>
        )}

        {/* Expanded View - "The Why" */}
        {expanded && (
          <div style={{ 
            marginTop: 12, 
            paddingTop: 12, 
            borderTop: '1px dashed #e2ece2',
            display: 'flex',
            flexDirection: 'column',
            gap: 12
          }}>
            {loadingExpl ? (
              <p style={{ fontSize: 12, color: '#8a9e8a' }}>Fetching explanation...</p>
            ) : (
              <div>
                <p style={{ fontSize: 11, fontWeight: 700, color: '#8a9e8a', textTransform: 'uppercase', marginBottom: 6 }}>Payout Explanation</p>
                <div style={{ background: '#f7f9f7', borderRadius: 12, padding: 12, fontSize: 13 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ color: '#4a5e4a' }}>Trigger Source</span>
                    <span style={{ fontWeight: 600 }}>{explanation?.trigger_source || triggerDetail.label || triggerType}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ color: '#4a5e4a' }}>Zone Match</span>
                    <span style={{ fontWeight: 600, color: explanation?.zone_match ? '#2a9e47' : '#dc2626' }}>
                      {explanation?.zone_match ? 'Verified' : 'Flagged'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ color: '#4a5e4a' }}>Payout Formula</span>
                    <span style={{ fontWeight: 600 }}>{explanation?.payout_formula || 'Determined by tier'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ color: '#4a5e4a' }}>Fraud Review</span>
                    <span style={{ fontWeight: 600 }}>{explanation?.fraud_decision || 'Passed'}</span>
                  </div>
                  {explanation?.fraud_score != null && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ color: '#4a5e4a' }}>Fraud Score</span>
                      <span style={{
                        fontWeight: 600,
                        color: explanation.fraud_score > 0.75 ? '#dc2626' : explanation.fraud_score > 0.5 ? '#f97316' : '#2a9e47'
                      }}>
                        {explanation.fraud_score.toFixed(2)}
                      </span>
                    </div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #e2ece2', marginTop: 8, paddingTop: 8 }}>
                    <span style={{ color: '#4a5e4a' }}>Transaction Proof</span>
                    <span style={{ fontWeight: 600, color: '#2a9e47', fontSize: 11 }}>{explanation?.transaction_proof || 'Processing'}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Consensus Meter */}
            <ConsensusMeter explanation={explanation} />

            {/* Fraud Decision Breakdown — split hard-stop vs ML triage */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {/* Model type label */}
              {explanation?.model_type && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#6b7280' }}>
                  <span style={{ background: '#f3f4f6', padding: '2px 8px', borderRadius: 20, fontWeight: 600 }}>
                    🤖 {explanation.model_type === 'isolation_forest' ? 'Anomaly Detection Model (Isolation Forest)'
                       : explanation.model_type === 'manual' ? 'Rule-Based Fallback Engine'
                       : explanation.model_type}
                  </span>
                </div>
              )}

              {/* Hard-stop reasons — deterministic rule violations */}
              {explanation?.hard_reject_reasons && explanation.hard_reject_reasons.length > 0 && (
                <div style={{ background: '#fef2f2', border: '1.5px solid #fecaca', borderRadius: 12, padding: 12 }}>
                  <p style={{ fontSize: 11, fontWeight: 800, color: '#991b1b', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                    🚫 Auto-Rejected by Rule Engine
                  </p>
                  <p style={{ fontSize: 10, color: '#b91c1c', marginBottom: 6, fontStyle: 'italic' }}>These are deterministic hard stops — ML is not involved</p>
                  <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, color: '#7f1d1d' }}>
                    {explanation.hard_reject_reasons.map((reason, idx) => (
                      <li key={idx} style={{ marginBottom: 4 }}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* ML triage signals — anomaly detection flags */}
              {explanation?.fraud_reasons && explanation.fraud_reasons.length > 0 && (
                <div style={{ background: '#fef3c7', border: '1.5px solid #fcd34d', borderRadius: 12, padding: 12 }}>
                  <p style={{ fontSize: 11, fontWeight: 800, color: '#92400e', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                    ⚠️ ML Triage Signals
                  </p>
                  <p style={{ fontSize: 10, color: '#b45309', marginBottom: 6, fontStyle: 'italic' }}>Anomaly detection flags — reviewed by insurer before final action</p>
                  <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, color: '#78350f' }}>
                    {explanation.fraud_reasons.map((reason, idx) => (
                      <li key={idx} style={{ marginBottom: 4 }}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {cityCap && (
              <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 12, padding: 10 }}>
                <p style={{ fontSize: 11, fontWeight: 700, color: '#92400e', marginBottom: 2 }}>City Hard Cap Status</p>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span>Current City BCR</span>
                  <span style={{ fontWeight: 600 }}>{(cityCap.current_ratio * 100).toFixed(1)}%</span>
                </div>
                <p style={{ fontSize: 10, color: '#b45309', marginTop: 4 }}>
                  Reinsurance active above 120%. Your payout is protected.
                </p>
              </div>
            )}

            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: 11, color: '#8a9e8a', marginBottom: 2 }}>Initiated</p>
                <p style={{ fontSize: 12, fontWeight: 600 }}>{fmtShort(createdAt)}</p>
              </div>
              {paidAt && (
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 11, color: '#2a9e47', marginBottom: 2 }}>Settled</p>
                  <p style={{ fontSize: 12, fontWeight: 600 }}>{fmtShort(paidAt)}</p>
                </div>
              )}
            </div>

            {upiRef && status === 'paid' && (
              <div style={{
                fontSize: 12,
                fontWeight: 700,
                color: upiRef.startsWith('tr_') ? '#4f46e5' : '#2a9e47',
                background: upiRef.startsWith('tr_') ? '#e0e7ff' : '#f0fdf4',
                padding: '8px 12px',
                borderRadius: 10,
              }}>
                <div style={{ fontSize: 10, opacity: 0.7, marginBottom: 2 }}>{upiRef.startsWith('tr_') ? 'Payment via Stripe Connect' : 'Payment via UPI Direct'}</div>
                {upiRef}
              </div>
            )}

            <p style={{ fontSize: 11, color: '#8a9e8a', textAlign: 'center', marginTop: 4 }}>Tap again to collapse</p>
          </div>
        )}

        {/* Payment state indicator */}
        {pCfg && paymentStatus !== 'not_started' && paymentStatus !== 'confirmed' && (
          <p style={{
            fontSize: 11,
            color: pCfg.color,
            background: `${pCfg.color}12`,
            padding: '4px 10px',
            borderRadius: 8,
            margin: 0,
            fontWeight: 600,
          }}>
            {pCfg.icon} {pCfg.label}
          </p>
        )}

        {/* Fraud score pill — always visible when score is notable */}
        {fraudScore != null && !expanded && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              fontSize: 11, fontWeight: 700,
              background: fraudScore > 0.75 ? '#fee2e2' : fraudScore > 0.5 ? '#fffbeb' : '#f0fdf4',
              color: fraudScore > 0.75 ? '#991b1b' : fraudScore > 0.5 ? '#b45309' : '#166534',
              border: `1px solid ${fraudScore > 0.75 ? '#fecaca' : fraudScore > 0.5 ? '#fde68a' : '#bbf7d0'}`,
              padding: '3px 10px', borderRadius: 20,
            }}>
              {fraudScore > 0.75 ? '🚫 High Risk' : fraudScore > 0.5 ? '⚠️ Under Review' : '✅ Low Risk'} · Score {fraudScore.toFixed(2)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

