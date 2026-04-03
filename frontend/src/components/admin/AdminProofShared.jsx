// frontend/src/components/admin/AdminProofShared.jsx
// Shared UI primitives for all proof panels

import React from 'react';

/**
 * Loading spinner with optional message.
 */
export function AdminLoader({ message = 'Loading…' }) {
  return (
    <div className="proof-loader">
      <div className="proof-loader__spinner" />
      <span className="proof-loader__text">{message}</span>
    </div>
  );
}

/**
 * Error card with optional retry.
 */
export function AdminError({ message = 'Something went wrong', onRetry }) {
  return (
    <div className="proof-error">
      <span className="proof-error__icon">⚠️</span>
      <p className="proof-error__message">{message}</p>
      {onRetry && (
        <button className="proof-error__retry" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

/**
 * Empty state with icon and message.
 */
export function AdminEmpty({ icon = '📭', message = 'No data available' }) {
  return (
    <div className="proof-empty">
      <span className="proof-empty__icon">{icon}</span>
      <p className="proof-empty__message">{message}</p>
    </div>
  );
}

/**
 * Source badge pill — shows data source provenance.
 *   live → green
 *   mixed / partial → amber
 *   mock / fallback → gray
 */
export function SourceBadge({ source }) {
  const s = (source || 'unknown').toLowerCase();
  let bg, color, label;

  if (s === 'live' || s === 'database') {
    bg = 'var(--green-light)'; color = 'var(--green-dark)'; label = `🟢 ${source}`;
  } else if (s === 'mixed' || s === 'partial') {
    bg = '#fef9c3'; color = 'var(--warning)'; label = `🟡 ${source}`;
  } else {
    bg = 'var(--gray-bg)'; color = 'var(--text-mid)'; label = `⚪ ${source}`;
  }

  return (
    <span className="source-badge" style={{ background: bg, color }}>
      {label}
    </span>
  );
}

/**
 * Pass / Fail / Partial badge.
 */
export function PassFailBadge({ status }) {
  const s = (status || '').toLowerCase();
  const cls =
    s === 'pass' ? 'proof-badge--pass'
    : s === 'fail' ? 'proof-badge--fail'
    : 'proof-badge--partial';

  return (
    <span className={`proof-badge ${cls}`}>
      {s === 'pass' ? '✅ PASS' : s === 'fail' ? '❌ FAIL' : '⚠️ PARTIAL'}
    </span>
  );
}

/**
 * Standard proof card wrapper.
 */
export function ProofCard({ title, subtitle, children, timestamp, source, passFail, style }) {
  return (
    <div className="admin-section proof-card" style={style}>
      <div className="proof-card__header">
        <div>
          <h3 className="proof-card__title">{title}</h3>
          {subtitle && <p className="proof-card__subtitle">{subtitle}</p>}
        </div>
        <div className="proof-card__badges">
          {passFail && <PassFailBadge status={passFail} />}
          {source && <SourceBadge source={source} />}
        </div>
      </div>
      <div className="proof-card__body">{children}</div>
      {timestamp && (
        <div className="proof-card__footer">
          Computed at {new Date(timestamp).toLocaleString('en-IN')}
        </div>
      )}
    </div>
  );
}
