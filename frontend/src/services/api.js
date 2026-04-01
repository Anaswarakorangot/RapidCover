const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class ApiService {
  constructor() {
    this.baseUrl = API_BASE;
  }

  getToken() {
    return localStorage.getItem('token');
  }

  setToken(token) {
    localStorage.setItem('token', token);
  }

  clearToken() {
    localStorage.removeItem('token');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getToken();

    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
      ...options,
    };

    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }

    const response = await fetch(url, config);

    if (response.status === 401) {
      this.clearToken();
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      // Handle FastAPI validation errors (detail is an array)
      let message = 'Request failed';
      if (typeof error.detail === 'string') {
        message = error.detail;
      } else if (Array.isArray(error.detail) && error.detail.length > 0) {
        message = error.detail[0].msg || error.detail[0].message || 'Validation error';
      }
      throw new Error(message);
    }

    return response.json();
  }

  // Auth
  async requestOTP(phone) {
    return this.request('/partners/login', {
      method: 'POST',
      body: { phone },
    });
  }

  async verifyOTP(phone, otp) {
    const data = await this.request('/partners/verify', {
      method: 'POST',
      body: { phone, otp },
    });
    this.setToken(data.access_token);
    return data;
  }

  async register(partnerData) {
    return this.request('/partners/register', {
      method: 'POST',
      body: partnerData,
    });
  }

  async validatePartnerId(partnerId, platform) {
    return this.request(
      `/partners/validate-id?partner_id=${encodeURIComponent(partnerId)}&platform=${encodeURIComponent(platform)}`
    );
  }

  // Partner
  async getProfile() {
    return this.request('/partners/me');
  }

  async updateProfile(data) {
    return this.request('/partners/me', {
      method: 'PATCH',
      body: data,
    });
  }

  // Policies
  async getPolicyQuotes() {
    return this.request('/policies/quotes');
  }

  async createPolicy(tier, autoRenew = true) {
    return this.request('/policies', {
      method: 'POST',
      body: { tier, auto_renew: autoRenew },
    });
  }

  async getActivePolicy() {
    return this.request('/policies/active');
  }

  async getPolicyHistory() {
    return this.request('/policies/history');
  }

  async cancelPolicy(policyId) {
    return this.request(`/policies/${policyId}/cancel`, {
      method: 'POST',
    });
  }

  async getRenewalQuote(policyId, tier = null) {
    const query = tier ? `?tier=${encodeURIComponent(tier)}` : '';
    return this.request(`/policies/${policyId}/renewal-quote${query}`);
  }

  async renewPolicy(policyId, tier = null, autoRenew = true) {
    return this.request(`/policies/${policyId}/renew`, {
      method: 'POST',
      body: { tier, auto_renew: autoRenew },
    });
  }

  async toggleAutoRenew(policyId, autoRenew) {
    return this.request(`/policies/${policyId}/auto-renew`, {
      method: 'PATCH',
      body: { auto_renew: autoRenew },
    });
  }

  async downloadCertificate(policyId) {
    const url = `${this.baseUrl}/policies/${policyId}/certificate`;
    const token = this.getToken();

    const response = await fetch(url, {
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to download certificate');
    }

    // Get filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'policy_certificate.pdf';
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/);
      if (match) {
        filename = match[1];
      }
    }

    // Download the blob
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }

  // Claims
  async getClaims(page = 1, pageSize = 10) {
    return this.request(`/claims?page=${page}&page_size=${pageSize}`);
  }

  async getClaimsSummary() {
    return this.request('/claims/summary');
  }

  async getClaim(claimId) {
    return this.request(`/claims/${claimId}`);
  }

  // Zones
  async getZones(city = null) {
    const query = city ? `?city=${encodeURIComponent(city)}` : '';
    return this.request(`/zones${query}`);
  }

  async getZone(zoneId) {
    return this.request(`/zones/${zoneId}`);
  }

  async getNearestZones(lat, lng, limit = 3) {
    return this.request(`/zones/nearest?lat=${lat}&lng=${lng}&limit=${limit}`);
  }

  // Triggers
  async getActiveTriggers(zoneId = null) {
    const query = zoneId ? `?zone_id=${zoneId}` : '';
    return this.request(`/triggers/active${query}`);
  }

  // Admin endpoints
  async getAdminDashboard() {
    return this.request('/admin/dashboard');
  }

  async seedZones() {
    return this.request('/admin/seed', { method: 'POST' });
  }

  async getAdminTriggers(activeOnly = false) {
    const query = activeOnly ? '?active_only=true' : '';
    return this.request(`/admin/triggers${query}`);
  }

  async getAdminClaims(statusFilter = null) {
    const query = statusFilter ? `?status_filter=${statusFilter}` : '';
    return this.request(`/admin/claims${query}`);
  }

  async simulateWeather(zoneId, rainfall_mm_hr = null, temp_celsius = null) {
    return this.request('/admin/simulate/weather', {
      method: 'POST',
      body: { zone_id: zoneId, rainfall_mm_hr, temp_celsius },
    });
  }

  async simulateAQI(zoneId, aqi) {
    return this.request('/admin/simulate/aqi', {
      method: 'POST',
      body: { zone_id: zoneId, aqi },
    });
  }

  async simulateShutdown(zoneId, reason) {
    return this.request('/admin/simulate/shutdown', {
      method: 'POST',
      body: { zone_id: zoneId, reason },
    });
  }

  async simulateClosure(zoneId, reason) {
    return this.request('/admin/simulate/closure', {
      method: 'POST',
      body: { zone_id: zoneId, reason },
    });
  }

  async processTrigger(triggerId) {
    return this.request(`/admin/triggers/${triggerId}/process`, { method: 'POST' });
  }

  async approveClaim(claimId) {
    return this.request(`/admin/claims/${claimId}/approve`, { method: 'POST' });
  }

  async rejectClaim(claimId, reason = null) {
    return this.request(`/admin/claims/${claimId}/reject`, {
      method: 'POST',
      body: { reason },
    });
  }

  async payoutClaim(claimId) {
    return this.request(`/admin/claims/${claimId}/payout`, { method: 'POST' });
  }

  async processAutoRenewals() {
    return this.request('/admin/process-auto-renewals', { method: 'POST' });
  }

  // Push Notifications
  async subscribePush(subscriptionData) {
    return this.request('/notifications/subscribe', {
      method: 'POST',
      body: subscriptionData,
    });
  }

  async unsubscribePush(endpoint = null) {
    return this.request('/notifications/unsubscribe', {
      method: 'POST',
      body: endpoint ? { endpoint } : {},
    });
  }

  async getNotificationStatus(endpoint = null) {
    const query = endpoint ? `?endpoint=${encodeURIComponent(endpoint)}` : '';
    return this.request(`/notifications/status${query}`);
  }
}

export const api = new ApiService();
export default api;
