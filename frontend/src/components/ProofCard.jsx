/**
 * ProofCard.jsx  –  Reusable proof / timestamp card
 *
 * B2 shared component. Used in Claims list, partner Dashboard, and demo proofs.
 *
 * Props:
 *   triggerType  {string}       'rain' | 'heat' | 'aqi' | 'shutdown' | 'closure'
 *   severity     {number?}      1–5, shown via SourceBadge
 *   status       {string}       'paid' | 'approved' | 'pending' | 'rejected'
 *   amount       {number?}      payout amount in ₹
 *   upiRef       {string?}      UPI reference (shown only for paid)
 *   createdAt    {string?}      ISO timestamp of claim / trigger creation
 *   paidAt       {string?}      ISO timestamp of payout
 *   metricValue  {string?}      Optional measurement label e.g. "87mm/hr", "AQI 410"
 *   fraudScore   {number?}      0.0–1.0 fraud score (shows warning if > 0.5)
 *   claimId      {number?}      Claim ID for reference
 */

import SourceBadge from './SourceBadge';

/* ─── Status config ──────────────────────────────────────────────────────── */
const STATUS_CFG = {
  paid:     { bg: '#dcfce7', color: '#166534', border: '#bbf7d0', icon: '✅', label: 'PAID' },
  approved: { bg: '#dbeafe', color: '#1e40af', border: '#bfdbfe', icon: '👍', label: 'APPROVED' },
  pending:  { bg: '#fef9c3', color: '#854d0e', border: '#fde68a', icon: '⏳', label: 'PENDING' },
  rejected: { bg: '#fee2e2', color: '#991b1b', border: '#fecaca', icon: '❌', label: 'REJECTED' },
};

const FALLBACK_STATUS = { bg: '#f3f4f6', color: '#374151', border: '#e5e7eb', icon: '•', label: 'UNKNOWN' };

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
}) {
  const stCfg = STATUS_CFG[status] || FALLBACK_STATUS;

  return (
    <div
      style={{
        background: '#ffffff',
        border: '1.5px solid #e2ece2',
        borderRadius: 18,
        overflow: 'hidden',
        fontFamily: "'DM Sans', sans-serif",
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
          {metricValue && (
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
              {metricValue}
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
          {stCfg.icon} {stCfg.label}
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
              ₹{amount}
            </span>
            {claimId && (
              <span style={{ fontSize: 11, color: '#8a9e8a' }}>· Claim #{claimId}</span>
            )}
          </div>
        )}

        {/* Timestamps */}
        {createdAt && (
          <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>
            🕐 {fmtDate(createdAt)}
          </p>
        )}
        {paidAt && (
          <p style={{ fontSize: 12, color: '#2a9e47', fontWeight: 600, margin: 0 }}>
            💸 Paid {fmtShort(paidAt)}
          </p>
        )}

        {/* Transfer reference */}
        {upiRef && status === 'paid' && (
          <p style={{
            fontSize: 12,
            fontWeight: 700,
            color: upiRef.startsWith('tr_') ? '#4f46e5' : '#2a9e47', // Stripe blurple vs UPI green
            background: upiRef.startsWith('tr_') ? '#e0e7ff' : '#f0fdf4',
            padding: '4px 10px',
            borderRadius: 8,
            margin: 0,
          }}>
            {upiRef.startsWith('tr_') ? '💳 Stripe Txn: ' : 'UPI Ref: '} {upiRef}
          </p>
        )}

        {/* Fraud warning */}
        {fraudScore != null && fraudScore > 0.5 && (
          <p style={{
            fontSize: 11,
            color: '#b45309',
            background: '#fffbeb',
            padding: '4px 10px',
            borderRadius: 8,
            margin: 0,
          }}>
            ⚠️ Under manual review (score: {fraudScore.toFixed(2)})
          </p>
        )}
      </div>
    </div>
  );
}
