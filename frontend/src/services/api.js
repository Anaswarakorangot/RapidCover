/**
 * api.js  –  RapidCover frontend API client
 *
 * Person 1 Phase 2 additions are in the "EXPERIENCE STATE" section at the bottom.
 * All existing methods are preserved unchanged.
 */

const BASE = '/api/v1';

// ── Shared helpers ────────────────────────────────────────────────────────────

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
    } catch (_) { }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

async function requestOtp(phone) {
  const res = await fetch(`${BASE}/partners/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  });
  return handleResponse(res);
}

async function verifyOtp(phone, otp) {
  const res = await fetch(`${BASE}/partners/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, otp }),
  });
  return handleResponse(res);
}

async function register(partnerData) {
  const res = await fetch(`${BASE}/partners/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(partnerData),
  });
  return handleResponse(res);
}

// ── Profile ───────────────────────────────────────────────────────────────────

async function getProfile() {
  const res = await fetch(`${BASE}/partners/me`, { headers: authHeaders() });
  return handleResponse(res);
}

async function updateProfile(data) {
  const res = await fetch(`${BASE}/partners/me`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

// ── Policies ──────────────────────────────────────────────────────────────────

async function getActivePolicy() {
  const res = await fetch(`${BASE}/policies/active`, { headers: authHeaders() });
  return handleResponse(res);
}

async function getPolicyHistory() {
  const res = await fetch(`${BASE}/policies/history`, { headers: authHeaders() });
  return handleResponse(res);
}

async function getPolicyQuotes() {
  const res = await fetch(`${BASE}/policies/quotes`, { headers: authHeaders() });
  return handleResponse(res);
}

async function createPolicy(tier, autoRenew = true) {
  const res = await fetch(`${BASE}/policies`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ tier, auto_renew: autoRenew }),
  });
  return handleResponse(res);
}

// ── Stripe Payments ────────────────────────────────────────────────────────────

async function createCheckoutSession(tier, autoRenew = false) {
  const res = await fetch(`${BASE}/payments/checkout?tier=${tier}&auto_renew=${autoRenew}`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return handleResponse(res);
}

async function confirmPayment(sessionId) {
  const res = await fetch(`${BASE}/payments/confirm?session_id=${encodeURIComponent(sessionId)}`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return handleResponse(res);
}

async function cancelPolicy(policyId) {
  const res = await fetch(`${BASE}/policies/${policyId}/cancel`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return handleResponse(res);
}

async function getRenewalQuote(policyId, tier = null) {
  const url = new URL(`${BASE}/policies/${policyId}/renewal-quote`, window.location.origin);
  if (tier) url.searchParams.set('tier', tier);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

async function renewPolicy(policyId, tier = null, autoRenew = true) {
  const res = await fetch(`${BASE}/policies/${policyId}/renew`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ tier, auto_renew: autoRenew }),
  });
  return handleResponse(res);
}

async function updateAutoRenew(policyId, autoRenew) {
  const res = await fetch(`${BASE}/policies/${policyId}/auto-renew`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify({ auto_renew: autoRenew }),
  });
  return handleResponse(res);
}

async function downloadCertificate(policyId) {
  const res = await fetch(`${BASE}/policies/${policyId}/certificate`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.blob();
}

// ── Claims ────────────────────────────────────────────────────────────────────

async function getClaimsSummary() {
  const res = await fetch(`${BASE}/claims/summary`, { headers: authHeaders() });
  return handleResponse(res);
}

async function getClaims(params = {}) {
  const url = new URL(`${BASE}/claims`, window.location.origin);
  Object.entries(params).forEach(([k, v]) => v != null && url.searchParams.set(k, v));
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

// ── Triggers ──────────────────────────────────────────────────────────────────

async function getActiveTriggers(zoneId = null) {
  const url = new URL(`${BASE}/triggers/active`, window.location.origin);
  if (zoneId) url.searchParams.set('zone_id', zoneId);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

async function getZone(zoneId) {
  const res = await fetch(`${BASE}/zones/${zoneId}`, { headers: authHeaders() });
  return handleResponse(res);
}

// ── Zones ─────────────────────────────────────────────────────────────────────

async function getZones(city = null) {
  const url = new URL(`${BASE}/zones`, window.location.origin);
  if (city) url.searchParams.set('city', city);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

async function getNearestZones(lat, lng) {
  const url = new URL(`${BASE}/zones/nearest`, window.location.origin);
  url.searchParams.set('lat', lat);
  url.searchParams.set('lng', lng);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

// ── RIQI ──────────────────────────────────────────────────────────────────────

async function getRiqiScores() {
  const res = await fetch(`${BASE}/partners/riqi`, { headers: authHeaders() });
  return handleResponse(res);
}

async function getCityRiqi(city) {
  const res = await fetch(`${BASE}/partners/riqi/${encodeURIComponent(city)}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// ── Premium (legacy – kept for backward compat) ───────────────────────────────

async function getPremiumQuotes(city, activeDays = 15, avgHours = 8, loyaltyWeeks = 0) {
  const url = new URL(`${BASE}/partners/quotes`, window.location.origin);
  url.searchParams.set('city', city);
  url.searchParams.set('active_days_last_30', activeDays);
  url.searchParams.set('avg_hours_per_day', avgHours);
  url.searchParams.set('loyalty_weeks', loyaltyWeeks);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

// ── Notifications ─────────────────────────────────────────────────────────────

async function getNotificationStatus(endpoint = null) {
  const url = new URL(`${BASE}/notifications/status`, window.location.origin);
  if (endpoint) url.searchParams.set('endpoint', endpoint);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

async function subscribePush(subscriptionData) {
  const res = await fetch(`${BASE}/notifications/subscribe`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(subscriptionData),
  });
  return handleResponse(res);
}

async function unsubscribePush(endpoint = null) {
  const res = await fetch(`${BASE}/notifications/unsubscribe`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ endpoint }),
  });
  return handleResponse(res);
}

// ── Validation ────────────────────────────────────────────────────────────────

async function validatePartnerId(partnerId, platform) {
  const url = new URL(`${BASE}/partners/validate-id`, window.location.origin);
  url.searchParams.set('partner_id', partnerId);
  url.searchParams.set('platform', platform);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

async function checkAvailability(phone, partnerId) {
  const url = new URL(`${BASE}/partners/check-availability`, window.location.origin);
  if (phone) url.searchParams.set('phone', phone);
  if (partnerId) url.searchParams.set('partner_id', partnerId);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

// ═══════════════════════════════════════════════════════════════════════════════
// EXPERIENCE STATE  –  Person 1, Phase 2
// These five methods replace every hardcoded constant in dashboard / profile / policy.
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Master dashboard state – replaces zoneReassignment, weatherAlert, streakWeeks.
 * Poll every 5 s during active drills.
 *
 * Response shape:
 * {
 *   zone_alert:        { type, message, severity, trigger_id, started_at } | null,
 *   zone_reassignment: { old_zone, new_zone, premium_delta, hours_left, ... } | null,
 *   loyalty:           { streak_weeks, discount_unlocked, next_milestone, discount_pct },
 *   premium_breakdown: { base, zone_risk, seasonal_index, riqi_adjustment,
 *                        activity_factor, loyalty_discount, total, city, riqi_band },
 *   latest_payout:     { claim_id, status:"paid", amount, upi_ref, paid_at } | null,
 *   fetched_at:        ISO string,
 * }
 */
async function getPartnerExperienceState() {
  const res = await fetch(`${BASE}/partners/me/experience-state`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/**
 * Itemised premium breakdown. Replaces ALL TIER_PRICES multiplier math in UI.
 */
async function getPremiumBreakdown() {
  const res = await fetch(`${BASE}/partners/me/premium-breakdown`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/**
 * Tier eligibility from backend. Frontend must use this to lock/unlock plan cards.
 *
 * Response: { active_days_last_30, loyalty_weeks, allowed_tiers, blocked_tiers, reasons, gate_blocked }
 */
async function getPartnerEligibility() {
  const res = await fetch(`${BASE}/partners/me/eligibility`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/**
 * Real zone history. Replaces MOCK_ZONE_HISTORY in Profile.jsx.
 *
 * Response: { history:[{old_zone_name, new_zone_name, new_zone_code, effective_at, ...}], total, has_history }
 */
async function getZoneHistory() {
  const res = await fetch(`${BASE}/partners/me/zone-history`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/**
 * Simplified renewal quote for profile page.
 * Replaces hardcoded renewal premium breakdown in Profile.jsx.
 */
async function getRenewalPreview() {
  const res = await fetch(`${BASE}/partners/me/renewal-preview`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// ── Default export ────────────────────────────────────────────────────────────

const api = {
  // Auth
  requestOtp,
  verifyOtp,
  register,
  // Profile
  getProfile,
  updateProfile,
  // Policies
  getActivePolicy,
  getPolicyHistory,
  getPolicyQuotes,
  createPolicy,
  createCheckoutSession,
  confirmPayment,
  cancelPolicy,
  getRenewalQuote,
  renewPolicy,
  updateAutoRenew,
  downloadCertificate,
  // Claims
  getClaimsSummary,
  getClaims,
  // Triggers
  getActiveTriggers,
  // Zones
  getZone,
  getZones,
  getNearestZones,
  // RIQI
  getRiqiScores,
  getCityRiqi,
  // Premium (legacy)
  getPremiumQuotes,
  // Notifications
  getNotificationStatus,
  subscribePush,
  unsubscribePush,
  // Validation
  validatePartnerId,
  checkAvailability,
  // ── Experience State (Person 1, Phase 2) ─────────────────────────────────────
  getPartnerExperienceState,
  getPremiumBreakdown,
  getPartnerEligibility,
  getZoneHistory,
  getRenewalPreview,
};

export default api;