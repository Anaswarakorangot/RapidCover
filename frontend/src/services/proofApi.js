/**
 * proofApi.js  –  Partner-side reassignment & proof API wrappers
 *
 * B2 owns this file.
 *
 * Covers:
 *   - Zone reassignment accept / reject (partner-initiated)
 *   - Active triggers enriched with source metadata
 *   - Countdown helpers driven by backend expires_at
 */

const BASE = import.meta.env.VITE_API_URL || '/api/v1';

// ── Shared helpers ─────────────────────────────────────────────────────────────

function getToken() {
  return localStorage.getItem('access_token');
}

function authHeaders() {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      // Failed to parse error response, use status only
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Zone Reassignment (partner-facing) ────────────────────────────────────────

/**
 * List all zone reassignment proposals for the logged-in partner.
 *
 * @returns {{ reassignments: ReassignmentResponse[], total: number, pending_count: number }}
 */
export async function getMyReassignments() {
  const res = await fetch(`${BASE}/partners/me/reassignments`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/**
 * Accept a pending zone reassignment proposal.
 * Updates partner.zone_id on the backend when successful.
 *
 * @param {number} reassignmentId
 * @returns {ZoneReassignmentActionResponse}
 */
export async function acceptReassignment(reassignmentId) {
  const res = await fetch(
    `${BASE}/partners/me/reassignments/${reassignmentId}/accept`,
    { method: 'POST', headers: authHeaders() }
  );
  return handleResponse(res);
}

/**
 * Reject a pending zone reassignment proposal.
 *
 * @param {number} reassignmentId
 * @returns {ZoneReassignmentActionResponse}
 */
export async function rejectReassignment(reassignmentId) {
  const res = await fetch(
    `${BASE}/partners/me/reassignments/${reassignmentId}/reject`,
    { method: 'POST', headers: authHeaders() }
  );
  return handleResponse(res);
}

// ── Trigger proofs ─────────────────────────────────────────────────────────────

/**
 * Get active trigger events, optionally filtered to a zone.
 *
 * @param {number|null} zoneId
 * @returns {{ triggers: TriggerEvent[] }}
 */
export async function getActiveTriggerProofs(zoneId = null) {
  const url = new URL(`${BASE}/triggers/active`, window.location.origin);
  if (zoneId) url.searchParams.set('zone_id', zoneId);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

// ── Countdown helpers ─────────────────────────────────────────────────────────

/**
 * Return hours and minutes remaining until an ISO expiry timestamp.
 *
 * @param {string} expiresAt  ISO 8601 string from backend
 * @returns {{ totalMs: number, hours: number, minutes: number, seconds: number, expired: boolean }}
 */
export function parseCountdown(expiresAt) {
  const diff = new Date(expiresAt).getTime() - Date.now();
  if (diff <= 0) {
    return { totalMs: 0, hours: 0, minutes: 0, seconds: 0, expired: true };
  }
  const totalSeconds = Math.floor(diff / 1000);
  return {
    totalMs: diff,
    hours: Math.floor(totalSeconds / 3600),
    minutes: Math.floor((totalSeconds % 3600) / 60),
    seconds: totalSeconds % 60,
    expired: false,
  };
}

/**
 * Format countdown into a human-readable label.
 *
 * @param {string} expiresAt
 * @returns {string}  e.g. "23h 14m left" | "Expired"
 */
export function formatCountdown(expiresAt) {
  const cd = parseCountdown(expiresAt);
  if (cd.expired) return 'Expired';
  if (cd.hours > 0) return `${cd.hours}h ${cd.minutes}m left`;
  if (cd.minutes > 0) return `${cd.minutes}m ${cd.seconds}s left`;
  return `${cd.seconds}s left`;
}

/**
 * Return CSS urgency class based on how much time is left.
 *
 * @param {string} expiresAt
 * @returns {'safe'|'warn'|'urgent'|'expired'}
 */
export function countdownUrgency(expiresAt) {
  const cd = parseCountdown(expiresAt);
  if (cd.expired) return 'expired';
  if (cd.hours >= 12) return 'safe';
  if (cd.hours >= 4) return 'warn';
  return 'urgent';
}

// ── Default export (named re-export for backward compat) ──────────────────────

const proofApi = {
  getMyReassignments,
  acceptReassignment,
  rejectReassignment,
  getActiveTriggerProofs,
  parseCountdown,
  formatCountdown,
  countdownUrgency,
};

export default proofApi;
