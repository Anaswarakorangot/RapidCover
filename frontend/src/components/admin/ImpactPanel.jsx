// frontend/src/components/admin/ImpactPanel.jsx
// Impact metrics display after drill completion

import { useState } from 'react';

export default function ImpactPanel({ impact }) {
  const [showSkipped, setShowSkipped] = useState(false);

  if (!impact) return null;

  const {
    affected_partners,
    eligible_partners,
    claims_created,
    claims_paid,
    claims_pending,
    payouts_total,
    skipped_partners,
    latency_metrics,
    status,
  } = impact;

  const statusColor = status === 'completed' ? 'var(--green-primary)' : status === 'failed' ? 'var(--error)' : 'var(--warning)';

  const metrics = [
    { label: 'Affected', value: affected_partners, desc: 'Partners in zone', color: 'var(--text-dark)' },
    { label: 'Eligible', value: eligible_partners, desc: 'With active policy', color: 'var(--green-primary)' },
    { label: 'Claims', value: claims_created, desc: 'Created', color: '#378ADD' },
    { label: 'Paid', value: claims_paid, desc: 'Auto-paid', color: 'var(--green-primary)' },
    { label: 'Pending', value: claims_pending, desc: 'In queue', color: 'var(--warning)' },
  ];

  const totalSkipped = Object.values(skipped_partners || {}).reduce((a, b) => a + b, 0);

  return (
    <div
      className="impact-panel"
      style={{
        background: 'var(--white)',
        borderRadius: '18px',
        border: '1.5px solid var(--border)',
        padding: '1.25rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1rem', color: 'var(--text-dark)' }}>
          Impact Summary
        </h3>
        <span
          style={{
            fontSize: '0.7rem',
            fontWeight: 800,
            padding: '0.25rem 0.6rem',
            borderRadius: '6px',
            background: `${statusColor}15`,
            color: statusColor,
            textTransform: 'uppercase',
          }}
        >
          {status}
        </span>
      </div>

      {/* Payout total */}
      <div
        style={{
          background: 'var(--green-light)',
          borderRadius: '14px',
          padding: '1rem',
          marginBottom: '1rem',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--green-dark)', textTransform: 'uppercase' }}>
          Total Payouts
        </div>
        <div style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.75rem', color: 'var(--green-primary)' }}>
          ₹{payouts_total?.toLocaleString() || 0}
        </div>
      </div>

      {/* Metrics grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', marginBottom: '1rem' }}>
        {metrics.map(m => (
          <div
            key={m.label}
            style={{
              background: 'var(--gray-bg)',
              borderRadius: '10px',
              padding: '0.75rem',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '0.6rem', fontWeight: 800, color: 'var(--text-light)', textTransform: 'uppercase' }}>
              {m.label}
            </div>
            <div style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.25rem', color: m.color }}>
              {m.value}
            </div>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-light)' }}>
              {m.desc}
            </div>
          </div>
        ))}
      </div>

      {/* Skipped partners */}
      {totalSkipped > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <button
            onClick={() => setShowSkipped(!showSkipped)}
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '0.75rem',
              background: '#fef9c3',
              border: '1px solid #d97706',
              borderRadius: '10px',
              cursor: 'pointer',
            }}
          >
            <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#92400e' }}>
              {totalSkipped} partners skipped
            </span>
            <span style={{ fontSize: '0.8rem' }}>{showSkipped ? '▲' : '▼'}</span>
          </button>

          {showSkipped && (
            <div style={{ marginTop: '0.5rem', padding: '0.75rem', background: 'var(--gray-bg)', borderRadius: '10px' }}>
              {Object.entries(skipped_partners).map(([reason, count]) => (
                <div
                  key={reason}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.35rem 0',
                    fontSize: '0.8rem',
                    borderBottom: '1px solid var(--border)',
                  }}
                >
                  <span style={{ color: 'var(--text-mid)' }}>{reason.replace(/_/g, ' ')}</span>
                  <span style={{ fontWeight: 700 }}>{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Latency metrics */}
      {latency_metrics && (
        <div>
          <div style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            Latency Breakdown
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            {latency_metrics.trigger_latency_ms != null && (
              <LatencyBar label="Trigger" value={latency_metrics.trigger_latency_ms} />
            )}
            {latency_metrics.claim_creation_latency_ms != null && (
              <LatencyBar label="Claims" value={latency_metrics.claim_creation_latency_ms} />
            )}
            {latency_metrics.payout_latency_ms != null && (
              <LatencyBar label="Payout" value={latency_metrics.payout_latency_ms} />
            )}
            {latency_metrics.total_latency_ms != null && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '0.5rem 0.75rem',
                  background: 'var(--green-light)',
                  borderRadius: '8px',
                  marginTop: '0.25rem',
                }}
              >
                <span style={{ fontWeight: 800, fontSize: '0.8rem', color: 'var(--green-dark)' }}>Total</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--green-primary)' }}>
                  {latency_metrics.total_latency_ms}ms
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function LatencyBar({ label, value }) {
  const maxWidth = 100;
  const width = Math.min((value / 1000) * 100, maxWidth); // Scale: 1000ms = 100%

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <span style={{ width: 60, fontSize: '0.75rem', color: 'var(--text-light)' }}>{label}</span>
      <div style={{ flex: 1, height: 6, background: 'var(--gray-bg)', borderRadius: 3, overflow: 'hidden' }}>
        <div
          style={{
            width: `${width}%`,
            height: '100%',
            background: value > 500 ? 'var(--warning)' : 'var(--green-primary)',
            borderRadius: 3,
            transition: 'width 0.3s ease',
          }}
        />
      </div>
      <span style={{ width: 50, fontFamily: 'monospace', fontSize: '0.7rem', textAlign: 'right', color: 'var(--text-mid)' }}>
        {value}ms
      </span>
    </div>
  );
}
