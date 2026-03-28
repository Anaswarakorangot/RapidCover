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
}

export const api = new ApiService();
export default api;
