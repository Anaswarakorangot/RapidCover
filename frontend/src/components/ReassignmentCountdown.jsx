/**
 * ReassignmentCountdown.jsx  –  Live countdown driven by backend expires_at
 *
 * B2 reusable component. Used in Dashboard ZoneReassignmentCard.
 *
 * Props:
 *   expiresAt  {string}  ISO 8601 UTC string from backend
 *   onExpire   {()=>void} optional callback when countdown hits zero
 */

import { useState, useEffect, useRef } from 'react';
import { parseCountdown, countdownUrgency } from '../services/proofApi';

/* ─── Styles ─────────────────────────────────────────────────────────────── */
const S = `
  .rcd-wrap {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'DM Sans', sans-serif;
    font-size: 12px;
    font-weight: 700;
    border-radius: 10px;
    padding: 3px 10px;
    transition: background 0.4s, color 0.4s;
  }

  /* Urgency states */
  .rcd-safe    { background: #dcfce7; color: #166534; }
  .rcd-warn    { background: #fef9c3; color: #854d0e; }
  .rcd-urgent  { background: #fee2e2; color: #991b1b; animation: rcd-pulse 1.2s ease-in-out infinite; }
  .rcd-expired { background: #f3f4f6; color: #6b7280; }

  .rcd-dot {
    width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
  }
  .rcd-safe   .rcd-dot { background: #22c55e; }
  .rcd-warn   .rcd-dot { background: #f59e0b; }
  .rcd-urgent .rcd-dot { background: #ef4444; }

  @keyframes rcd-pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.55; }
  }
`;

/* ─── Component ──────────────────────────────────────────────────────────── */
export default function ReassignmentCountdown({ expiresAt, onExpire }) {
  const [cd, setCd] = useState(() => parseCountdown(expiresAt));
  const firedRef = useRef(false);

  useEffect(() => {
    if (!expiresAt) return;
    const tick = () => {
      const next = parseCountdown(expiresAt);
      setCd(next);
      if (next.expired && !firedRef.current) {
        firedRef.current = true;
        onExpire?.();
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [expiresAt, onExpire]);

  const urgency = countdownUrgency(expiresAt);

  let label;
  if (cd.expired) {
    label = 'Expired';
  } else if (cd.hours > 0) {
    label = `${cd.hours}h ${cd.minutes}m left`;
  } else if (cd.minutes > 0) {
    label = `${cd.minutes}m ${cd.seconds}s left`;
  } else {
    label = `${cd.seconds}s left`;
  }

  return (
    <>
      <style>{S}</style>
      <span className={`rcd-wrap rcd-${urgency}`} role="timer" aria-live="polite">
        {urgency !== 'expired' && <span className="rcd-dot" />}
        {label}
      </span>
    </>
  );
}
