/* global global */
/**
 * apiIntegration.test.js  –  API client fetch-layer integration tests
 *
 * Covers:
 *   - proofApi: getMyReassignments, acceptReassignment, rejectReassignment
 *   - api.js: getPartnerExperienceState response shape, getActiveTriggers
 *   - adminApi: getDashboardStats, simulateWeather, approveClaim
 *
 * All tests use vi.stubGlobal('fetch', ...) — no real network calls.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// ── Modules under test ─────────────────────────────────────────────────────
import {
  getMyReassignments,
  acceptReassignment,
  rejectReassignment,
  getActiveTriggerProofs,
} from '../services/proofApi';

import api from '../services/api';
import adminApi from '../services/adminApi';

// ── Helpers ────────────────────────────────────────────────────────────────

/** Build a fake Response object that resolves to the given JSON body */
function mockFetch(body, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

/** Extract the URL that the last fetch call was made to */
function lastUrl() {
  const calls = global.fetch.mock.calls;
  return calls[calls.length - 1][0];
}

/** Extract the init (method, headers, body) of the last fetch call */
function lastInit() {
  const calls = global.fetch.mock.calls;
  return calls[calls.length - 1][1];
}

beforeEach(() => {
  // Reset localStorage token for each test
  localStorage.clear();
  localStorage.setItem('access_token', 'test-jwt-token');
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ═══════════════════════════════════════════════════════════════════════════
// proofApi — zone reassignment
// ═══════════════════════════════════════════════════════════════════════════

describe('proofApi.getMyReassignments', () => {
  it('calls GET /api/v1/partners/me/reassignments', async () => {
    const payload = { reassignments: [], total: 0, pending_count: 0 };
    global.fetch = mockFetch(payload);

    const result = await getMyReassignments();

    expect(lastUrl()).toContain('/api/v1/partners/me/reassignments');
    // GET calls: no method override (undefined = GET) and no request body
    expect(lastInit()?.method).toBeUndefined();
    expect(lastInit()?.body).toBeUndefined();
    expect(result).toEqual(payload);
  });

  it('attaches Authorization header', async () => {
    global.fetch = mockFetch({ reassignments: [] });
    await getMyReassignments();
    const headers = global.fetch.mock.calls[0][1]?.headers || {};
    expect(headers['Authorization']).toBe('Bearer test-jwt-token');
  });

  it('throws on non-ok response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Unauthorized' }),
    });
    await expect(getMyReassignments()).rejects.toThrow('Unauthorized');
  });
});

describe('proofApi.acceptReassignment', () => {
  it('calls POST /api/v1/partners/me/reassignments/7/accept', async () => {
    const payload = { id: 7, status: 'accepted', message: 'Zone reassignment accepted successfully', zone_updated: true };
    global.fetch = mockFetch(payload);

    const result = await acceptReassignment(7);

    expect(lastUrl()).toContain('/api/v1/partners/me/reassignments/7/accept');
    expect(lastInit()?.method).toBe('POST');
    expect(result.status).toBe('accepted');
  });

  it('throws with backend detail on failure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Reassignment proposal has expired' }),
    });
    await expect(acceptReassignment(99)).rejects.toThrow('Reassignment proposal has expired');
  });
});

describe('proofApi.rejectReassignment', () => {
  it('calls POST /api/v1/partners/me/reassignments/3/reject', async () => {
    global.fetch = mockFetch({ id: 3, status: 'rejected', message: 'Zone reassignment rejected', zone_updated: false });

    await rejectReassignment(3);

    expect(lastUrl()).toContain('/api/v1/partners/me/reassignments/3/reject');
    expect(lastInit()?.method).toBe('POST');
  });
});

describe('proofApi.getActiveTriggerProofs', () => {
  it('calls /api/v1/triggers/active without zone filter', async () => {
    global.fetch = mockFetch({ triggers: [] });
    await getActiveTriggerProofs();
    expect(lastUrl()).toContain('/api/v1/triggers/active');
    expect(lastUrl()).not.toContain('zone_id');
  });

  it('adds zone_id query param when provided', async () => {
    global.fetch = mockFetch({ triggers: [] });
    await getActiveTriggerProofs(5);
    expect(lastUrl()).toContain('zone_id=5');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// api.js — experience state
// ═══════════════════════════════════════════════════════════════════════════

describe('api.getPartnerExperienceState', () => {
  it('calls GET /api/v1/partners/me/experience-state', async () => {
    const payload = {
      zone_alert: null,
      zone_reassignment: null,
      loyalty: { streak_weeks: 3, discount_unlocked: false, next_milestone: 4, discount_pct: 3 },
      premium_breakdown: { base: 33, total: 38 },
      latest_payout: null,
      fetched_at: new Date().toISOString(),
    };
    global.fetch = mockFetch(payload);

    const result = await api.getPartnerExperienceState();

    expect(lastUrl()).toContain('/api/v1/partners/me/experience-state');
    expect(result.loyalty.streak_weeks).toBe(3);
    expect(result.zone_alert).toBeNull();
  });

  it('includes Authorization header', async () => {
    global.fetch = mockFetch({ loyalty: {} });
    await api.getPartnerExperienceState();
    const headers = global.fetch.mock.calls[0][1]?.headers || {};
    expect(headers['Authorization']).toBe('Bearer test-jwt-token');
  });
});

describe('api.getActiveTriggers', () => {
  it('calls /api/v1/triggers/active with no params when zoneId omitted', async () => {
    global.fetch = mockFetch({ triggers: [] });
    await api.getActiveTriggers();
    expect(lastUrl()).toContain('/api/v1/triggers/active');
  });

  it('adds zone_id param when provided', async () => {
    global.fetch = mockFetch({ triggers: [] });
    await api.getActiveTriggers(3);
    expect(lastUrl()).toContain('zone_id=3');
  });
});

describe('api.getClaims', () => {
  it('calls /api/v1/claims with limit param', async () => {
    global.fetch = mockFetch([]);
    await api.getClaims({ limit: 5 });
    expect(lastUrl()).toContain('/api/v1/claims');
    expect(lastUrl()).toContain('limit=5');
  });
});

describe('api.createPolicy', () => {
  it('POSTs to /api/v1/policies with correct body', async () => {
    global.fetch = mockFetch({ id: 1, tier: 'standard', is_active: true });
    await api.createPolicy('standard', true);
    expect(lastUrl()).toContain('/api/v1/policies');
    expect(lastInit()?.method).toBe('POST');
    const body = JSON.parse(lastInit()?.body);
    expect(body.tier).toBe('standard');
    expect(body.auto_renew).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// adminApi
// ═══════════════════════════════════════════════════════════════════════════

describe('adminApi.getDashboardStats', () => {
  it('calls GET /api/v1/admin/dashboard', async () => {
    const payload = {
      total_partners: 10,
      active_policies: 6,
      total_zones: 11,
      active_triggers: 1,
      pending_claims: 2,
      approved_claims: 3,
      total_paid_amount: 750.0,
    };
    global.fetch = mockFetch(payload);
    const result = await adminApi.getDashboardStats();
    expect(lastUrl()).toContain('/api/v1/admin/dashboard');
    expect(result.total_partners).toBe(10);
  });
});

describe('adminApi.simulateWeather', () => {
  it('POSTs to /api/v1/admin/simulate/weather with zone_id and params', async () => {
    global.fetch = mockFetch({ zone_id: 2, triggers_created: [5] });
    await adminApi.simulateWeather(2, { rainfall_mm_hr: 90 });
    expect(lastUrl()).toContain('/api/v1/admin/simulate/weather');
    const body = JSON.parse(lastInit()?.body);
    expect(body.zone_id).toBe(2);
    expect(body.rainfall_mm_hr).toBe(90);
  });
});

describe('adminApi.approveClaim', () => {
  it('POSTs to /api/v1/admin/claims/14/approve', async () => {
    global.fetch = mockFetch({ message: 'Claim approved', claim_id: 14 });
    await adminApi.approveClaim(14);
    expect(lastUrl()).toContain('/api/v1/admin/claims/14/approve');
    expect(lastInit()?.method).toBe('POST');
  });
});

describe('adminApi.rejectClaim', () => {
  it('POSTs with reason when provided', async () => {
    global.fetch = mockFetch({ message: 'Claim rejected', claim_id: 11 });
    await adminApi.rejectClaim(11, 'fraud detected');
    const body = JSON.parse(lastInit()?.body);
    expect(body.reason).toBe('fraud detected');
  });

  it('POSTs with null body when no reason given', async () => {
    global.fetch = mockFetch({ message: 'Claim rejected' });
    await adminApi.rejectClaim(11);
    // fetch called with no body (null passed)
    expect(lastInit()?.body).toBeUndefined();
  });
});

describe('adminApi.previewNotification', () => {
  it('calls GET /api/v1/admin/panel/notifications/preview with type and lang', async () => {
    global.fetch = mockFetch({ type: 'claim_paid', language: 'hi', title: 'भुगतान प्राप्त!' });
    await adminApi.previewNotification('claim_paid', 'hi');
    expect(lastUrl()).toContain('/api/v1/admin/panel/notifications/preview');
    expect(lastUrl()).toContain('type=claim_paid');
    expect(lastUrl()).toContain('lang=hi');
  });
});

describe('adminApi.getStressScenarios', () => {
  it('calls GET /api/v1/admin/panel/stress-scenarios', async () => {
    global.fetch = mockFetch([]);
    await adminApi.getStressScenarios();
    expect(lastUrl()).toContain('/api/v1/admin/panel/stress-scenarios');
  });
});
