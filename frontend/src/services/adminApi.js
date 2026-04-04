/**
 * adminApi.js  –  Admin API client wrappers
 *
 * B2 owns shared API helpers; B1 admin components import from here.
 *
 * All calls go to /api/v1/admin/*
 * Admin endpoints are intentionally unauthenticated in this demo.
 */

const BASE = '/api/v1/admin';

// ── Shared helpers ─────────────────────────────────────────────────────────────

function getToken() {
  return localStorage.getItem('access_token');
}

function jsonHeaders() {
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

async function get(path, params = {}) {
  const url = new URL(`${BASE}${path}`, window.location.origin);
  Object.entries(params).forEach(([k, v]) => v != null && url.searchParams.set(k, v));
  const res = await fetch(url.toString(), { headers: jsonHeaders() });
  return handleResponse(res);
}

async function post(path, body = null) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: jsonHeaders(),
    ...(body != null ? { body: JSON.stringify(body) } : {}),
  });
  return handleResponse(res);
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

/** @returns {DashboardStats} */
export async function getDashboardStats() {
  return get('/dashboard');
}

// ── Zones ─────────────────────────────────────────────────────────────────────

export async function getAllZones() {
  return get('/zones');
}

export async function seedZones() {
  return post('/seed');
}

// ── Trigger management ────────────────────────────────────────────────────────

/**
 * @param {{ active_only?: boolean, zone_id?: number, skip?: number, limit?: number }} params
 */
export async function getTriggers(params = {}) {
  return get('/triggers', params);
}

export async function endTrigger(triggerId) {
  return post(`/triggers/${triggerId}/end`);
}

export async function processTrigger(triggerId) {
  return post(`/triggers/${triggerId}/process`);
}

// ── Claims management ─────────────────────────────────────────────────────────

/**
 * @param {{ status_filter?: string, zone_id?: number, skip?: number, limit?: number }} params
 */
export async function getAdminClaims(params = {}) {
  return get('/claims', params);
}

export async function approveClaim(claimId) {
  return post(`/claims/${claimId}/approve`);
}

export async function rejectClaim(claimId, reason = null) {
  return post(`/claims/${claimId}/reject`, reason ? { reason } : null);
}

export async function payoutClaim(claimId, upiRef = null) {
  return post(`/claims/${claimId}/payout`, upiRef ? { upi_ref: upiRef } : null);
}

// ── Simulation ────────────────────────────────────────────────────────────────

/**
 * @param {number} zoneId
 * @param {{ temp_celsius?: number, rainfall_mm_hr?: number, humidity?: number }} params
 */
export async function simulateWeather(zoneId, params = {}) {
  return post('/simulate/weather', { zone_id: zoneId, ...params });
}

/**
 * @param {number} zoneId
 * @param {{ aqi?: number, pm25?: number, pm10?: number }} params
 */
export async function simulateAqi(zoneId, params = {}) {
  return post('/simulate/aqi', { zone_id: zoneId, ...params });
}

export async function simulateShutdown(zoneId, reason = 'Civic shutdown - curfew in effect') {
  return post('/simulate/shutdown', { zone_id: zoneId, reason });
}

export async function simulateClosure(zoneId, reason = 'Force majeure - infrastructure issue') {
  return post('/simulate/closure', { zone_id: zoneId, reason });
}

export async function clearZoneConditions(zoneId) {
  return post(`/simulate/clear/${zoneId}`);
}

export async function resetAllSimulations() {
  return post('/simulate/reset');
}

export async function processAutoRenewals() {
  return post('/process-auto-renewals');
}

// ── Admin Panel – Stress Scenarios ────────────────────────────────────────────

export async function getStressScenarios() {
  return get('/panel/stress-scenarios');
}

export async function getStressScenario(scenarioId) {
  return get(`/panel/stress-scenarios/${scenarioId}`);
}

// ── Admin Panel – RIQI ────────────────────────────────────────────────────────

export async function getRiqiProfiles() {
  return get('/panel/riqi');
}

export async function getRiqiForZone(zoneCode) {
  return get(`/panel/riqi/${zoneCode}`);
}

export async function recomputeRiqi(zoneCode) {
  return post(`/panel/riqi/${zoneCode}/recompute`);
}

export async function seedRiqiProfiles() {
  return post('/panel/riqi/seed');
}

// ── Admin Panel – Notification Templates ─────────────────────────────────────

/**
 * Preview a notification template with sample data.
 * @param {string} type  e.g. 'claim_created'
 * @param {string} lang  e.g. 'en', 'hi'
 */
export async function previewNotification(type = 'claim_created', lang = 'en') {
  return get('/panel/notifications/preview', { type, lang });
}

export async function listNotificationTemplates() {
  return get('/panel/notifications/templates');
}

// ── Admin Panel – Trigger eligibility check ───────────────────────────────────

export async function checkTriggerEligibility(partnerId, zoneId, triggerType = 'rain') {
  return post('/panel/trigger-check', {
    partner_id: partnerId,
    zone_id: zoneId,
    trigger_type: triggerType,
  });
}

// ── Zone Reassignment (admin-side) ────────────────────────────────────────────

export async function proposeReassignment(partnerId, newZoneId) {
  const res = await fetch(`/api/v1/admin/reassignments`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ partner_id: partnerId, new_zone_id: newZoneId }),
  });
  return handleResponse(res);
}

// ── Multi-Trigger Aggregation ─────────────────────────────────────────────────

/** Get aggregation stats (total aggregated claims, triggers suppressed, savings) */
export async function getAggregationStats() {
  return get('/aggregation-stats');
}

/** Get aggregation details for a specific claim */
export async function getClaimAggregation(claimId) {
  return get(`/claims/${claimId}/aggregation`);
}

// ── Payment State Machine ─────────────────────────────────────────────────────

/** Get payment state for a specific claim */
export async function getClaimPaymentState(claimId) {
  return get(`/claims/${claimId}/payment-state`);
}

/** Retry a failed payment */
export async function retryPayment(claimId) {
  return post(`/claims/${claimId}/retry-payment`);
}

/**
 * Manually reconcile a payment.
 * @param {number} claimId
 * @param {{ action: 'confirm'|'reject'|'force_paid', provider_ref?: string, notes?: string }} data
 */
export async function reconcilePayment(claimId, data) {
  return post(`/claims/${claimId}/reconcile`, data);
}

/** List claims with failed payments */
export async function getPaymentFailures(limit = 50) {
  return get('/claims/payment-failures', { limit });
}

/** List claims pending manual reconciliation */
export async function getPendingReconciliation(limit = 50) {
  return get('/claims/pending-reconciliation', { limit });
}

/** Get payment processing statistics */
export async function getPaymentStats() {
  return get('/payment-stats');
}

// ── Default export ────────────────────────────────────────────────────────────

const adminApi = {
  getDashboardStats,
  getAllZones,
  seedZones,
  getTriggers,
  endTrigger,
  processTrigger,
  getAdminClaims,
  approveClaim,
  rejectClaim,
  payoutClaim,
  simulateWeather,
  simulateAqi,
  simulateShutdown,
  simulateClosure,
  clearZoneConditions,
  resetAllSimulations,
  processAutoRenewals,
  getStressScenarios,
  getStressScenario,
  getRiqiProfiles,
  getRiqiForZone,
  recomputeRiqi,
  seedRiqiProfiles,
  previewNotification,
  listNotificationTemplates,
  checkTriggerEligibility,
  proposeReassignment,
  // Multi-trigger aggregation
  getAggregationStats,
  getClaimAggregation,
  // Payment state machine
  getClaimPaymentState,
  retryPayment,
  reconcilePayment,
  getPaymentFailures,
  getPendingReconciliation,
  getPaymentStats,
};

export default adminApi;

// ── Validation Matrix ──────────────────────────────────────────────────────────

/** Get validation matrix proof (most recent claim with matrix) */
export async function getValidationMatrixProof() {
  return get('/panel/proof/validation-matrix');
}

/** Get validation matrix for a specific claim */
export async function getClaimValidationMatrix(claimId) {
  return get(`/claims/${claimId}/validation-matrix`);
}

// ── Oracle Reliability ────────────────────────────────────────────────────────

/** Get oracle reliability proof (source confidence + trigger decisions) */
export async function getOracleReliabilityProof() {
  return get('/panel/proof/oracle-reliability');
}

/** Get full oracle reliability report (optionally filtered to a zone_id) */
export async function getOracleReliability(zoneId = null) {
  const url = new URL(`${BASE}/panel/oracle-reliability`, window.location.origin);
  if (zoneId) url.searchParams.set('zone_id', zoneId);
  const res = await fetch(url.toString(), { headers: jsonHeaders() });
  return handleResponse(res);
}

// ── Platform Activity ──────────────────────────────────────────────────────────

/** Get platform activity proof (fleet-level summary) */
export async function getPlatformActivityProof() {
  return get('/panel/proof/platform-activity');
}

/** Get live data panel (oracle + sources + platform activity combined) */
export async function getLiveData(zoneCode = null) {
  const params = zoneCode ? { zone_code: zoneCode } : {};
  return get('/panel/live-data', params);
}