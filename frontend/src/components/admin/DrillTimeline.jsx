// frontend/src/components/admin/DrillTimeline.jsx
// Real-time vertical timeline showing drill pipeline events

import { useEffect, useRef } from 'react';

const STEP_COLORS = {
  injected: '#378ADD',
  threshold_crossed: '#EF9F27',
  trigger_fired: '#E24B4A',
  eligible_partners_found: '#3DB85C',
  claims_created: '#3DB85C',
  fraud_scored: '#9333ea',
  payouts_sent: '#3DB85C',
  notifications_sent: '#7F77DD',
  completed: '#3DB85C',
  error: '#E24B4A',
};

const STEP_ICONS = {
  injected: '💉',
  threshold_crossed: '⚡',
  trigger_fired: '🔥',
  eligible_partners_found: '👥',
  claims_created: '📋',
  fraud_scored: '🛡️',
  payouts_sent: '💸',
  notifications_sent: '🔔',
  completed: '✅',
  error: '❌',
};

const STEP_LABELS = {
  injected: 'Conditions Injected',
  threshold_crossed: 'Threshold Crossed',
  trigger_fired: 'Trigger Fired',
  eligible_partners_found: 'Partners Found',
  claims_created: 'Claims Created',
  fraud_scored: 'Fraud Scored',
  payouts_sent: 'Payouts Sent',
  notifications_sent: 'Notifications',
  completed: 'Completed',
  error: 'Error',
};

export default function DrillTimeline({ events, drillId }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events]);

  if (!events || events.length === 0) {
    return null;
  }

  return (
    <div
      className="drill-timeline"
      style={{
        background: 'var(--white)',
        borderRadius: '18px',
        border: '1.5px solid var(--border)',
        padding: '1.25rem',
        maxHeight: '500px',
        overflowY: 'auto',
      }}
    >
      <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1rem', color: 'var(--text-dark)' }}>
          Pipeline Timeline
        </h3>
        {drillId && (
          <code style={{ fontSize: '0.7rem', color: 'var(--text-light)', background: 'var(--gray-bg)', padding: '0.25rem 0.5rem', borderRadius: '6px' }}>
            {drillId.slice(0, 8)}...
          </code>
        )}
      </div>

      <div className="timeline-events" style={{ position: 'relative', paddingLeft: '2rem' }}>
        {/* Vertical line */}
        <div
          style={{
            position: 'absolute',
            left: '0.5rem',
            top: '0.5rem',
            bottom: '0.5rem',
            width: 2,
            background: 'var(--border)',
          }}
        />

        {events.map((event, idx) => {
          const color = STEP_COLORS[event.step] || '#888';
          const icon = STEP_ICONS[event.step] || '•';
          const label = STEP_LABELS[event.step] || event.step;
          const isLast = idx === events.length - 1;
          const isCompleted = event.step === 'completed';
          const isError = event.step === 'error';

          return (
            <div
              key={idx}
              className="timeline-event"
              style={{
                position: 'relative',
                paddingBottom: isLast ? 0 : '1rem',
                animation: 'fadeInUp 0.3s ease',
              }}
            >
              {/* Dot */}
              <div
                style={{
                  position: 'absolute',
                  left: '-1.75rem',
                  top: '0.1rem',
                  width: 20,
                  height: 20,
                  borderRadius: '50%',
                  background: color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.65rem',
                  boxShadow: `0 0 0 3px ${color}20`,
                }}
              >
                {icon}
              </div>

              {/* Content */}
              <div
                style={{
                  background: isCompleted ? 'var(--green-light)' : isError ? '#fef2f2' : 'var(--gray-bg)',
                  borderRadius: '12px',
                  padding: '0.75rem 1rem',
                  borderLeft: `3px solid ${color}`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.25rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dark)' }}>
                    {label}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-light)' }}>
                    {new Date(event.ts).toLocaleTimeString()}
                  </span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-mid)', margin: 0, lineHeight: 1.4 }}>
                  {event.message}
                </p>

                {/* Metadata badges */}
                {event.metadata && Object.keys(event.metadata).length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.5rem' }}>
                    {Object.entries(event.metadata).map(([key, val]) => {
                      if (key === 'conditions' || key === 'error') return null;
                      return (
                        <span
                          key={key}
                          style={{
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            padding: '0.15rem 0.4rem',
                            borderRadius: '4px',
                            background: `${color}15`,
                            color: color,
                          }}
                        >
                          {key}: {typeof val === 'number' ? val.toLocaleString() : String(val)}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        <div ref={bottomRef} />
      </div>

      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
