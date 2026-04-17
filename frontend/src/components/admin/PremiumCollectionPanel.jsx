import { useState, useEffect } from 'react';
import { adminFetch } from '../../services/adminApi';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export default function PremiumCollectionPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ tier: 'all', city: 'all', status: 'all' });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const res = await adminFetch(`${API_BASE}/admin/panel/premium-collection`);
      if (!res.ok) throw new Error('Failed to load premium collection data');
      setData(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="admin-section">
        <div className="proof-loader">
          <div className="proof-loader__spinner" />
          <span className="proof-loader__text">Loading premium collection data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-section">
        <div className="proof-error">
          <span className="proof-error__icon">❌</span>
          <span className="proof-error__message">{error}</span>
          <button className="proof-error__retry" onClick={loadData}>Retry</button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="admin-section">
        <div className="proof-empty">
          <span className="proof-empty__icon">📊</span>
          <span className="proof-empty__message">No premium data available</span>
        </div>
      </div>
    );
  }

  const summary = data.summary || {};
  const policies = data.policies || [];
  const weeklyTrend = data.weekly_trend || [];
  const cities = [...new Set(policies.map(p => p.city))].sort();
  const tiers = ['flex', 'standard', 'pro'];

  // Apply filters
  const filteredPolicies = policies.filter(p => {
    if (filters.tier !== 'all' && p.tier !== filters.tier) return false;
    if (filters.city !== 'all' && p.city !== filters.city) return false;
    if (filters.status !== 'all' && p.payment_status !== filters.status) return false;
    return true;
  });

  // Group by status
  const paidPolicies = filteredPolicies.filter(p => p.payment_status === 'paid');
  const unpaidPolicies = filteredPolicies.filter(p => p.payment_status === 'unpaid');
  const overduePolicies = filteredPolicies.filter(p => p.payment_status === 'overdue');

  const collectionRate = summary.total_expected > 0
    ? Math.round((summary.total_collected / summary.total_expected) * 100)
    : 0;

  return (
    <div className="admin-section">
      <div className="admin-section-label">PREMIUM COLLECTION</div>

      {/* Summary cards */}
      <div className="proof-metrics-grid" style={{ marginBottom: '2rem' }}>
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">Total Collected</span>
          <span className="proof-metric-card__value" style={{ color: 'var(--green-primary)' }}>
            ₹{(summary.total_collected / 1000).toFixed(1)}K
          </span>
        </div>
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">Total Unpaid</span>
          <span className="proof-metric-card__value" style={{ color: 'var(--warning)' }}>
            ₹{(summary.total_unpaid / 1000).toFixed(1)}K
          </span>
        </div>
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">Collection Rate</span>
          <span className="proof-metric-card__value" style={{ color: collectionRate >= 80 ? 'var(--green-primary)' : 'var(--warning)' }}>
            {collectionRate}%
          </span>
        </div>
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">Active Policies</span>
          <span className="proof-metric-card__value" style={{ color: 'var(--text-dark)' }}>
            {summary.active_policies || 0}
          </span>
        </div>
      </div>

      {/* Weekly trend */}
      {weeklyTrend.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <p style={{ fontFamily: 'Nunito', fontWeight: 800, fontSize: '1rem', marginBottom: '1rem', color: 'var(--text-dark)' }}>
            Weekly Collection Trend
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end', height: '120px' }}>
            {weeklyTrend.map((week, i) => {
              const maxAmount = Math.max(...weeklyTrend.map(w => w.collected));
              const height = maxAmount > 0 ? (week.collected / maxAmount) * 100 : 0;
              return (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                  <div
                    style={{
                      width: '100%',
                      height: `${height}%`,
                      background: 'var(--green-primary)',
                      borderRadius: '6px 6px 0 0',
                      minHeight: '4px',
                      position: 'relative',
                    }}
                    title={`₹${week.collected}`}
                  />
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-light)', fontWeight: 600 }}>
                    W{week.week}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-light)' }}>
            Tier
          </label>
          <select
            value={filters.tier}
            onChange={e => setFilters({ ...filters, tier: e.target.value })}
            style={{
              padding: '0.5rem 0.75rem',
              border: '1.5px solid var(--border)',
              borderRadius: '10px',
              background: 'var(--white)',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            <option value="all">All Tiers</option>
            {tiers.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
          </select>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-light)' }}>
            City
          </label>
          <select
            value={filters.city}
            onChange={e => setFilters({ ...filters, city: e.target.value })}
            style={{
              padding: '0.5rem 0.75rem',
              border: '1.5px solid var(--border)',
              borderRadius: '10px',
              background: 'var(--white)',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            <option value="all">All Cities</option>
            {cities.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-light)' }}>
            Status
          </label>
          <select
            value={filters.status}
            onChange={e => setFilters({ ...filters, status: e.target.value })}
            style={{
              padding: '0.5rem 0.75rem',
              border: '1.5px solid var(--border)',
              borderRadius: '10px',
              background: 'var(--white)',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            <option value="all">All Status</option>
            <option value="paid">Paid</option>
            <option value="unpaid">Unpaid</option>
            <option value="overdue">Overdue</option>
          </select>
        </div>
      </div>

      {/* Payment status tabs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{
          padding: '1rem',
          background: 'var(--white)',
          border: '1.5px solid var(--border)',
          borderRadius: '16px',
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-light)', marginBottom: '0.5rem' }}>
            Paid
          </div>
          <div style={{ fontFamily: 'Nunito', fontSize: '1.5rem', fontWeight: 900, color: 'var(--green-primary)' }}>
            {paidPolicies.length}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-mid)', marginTop: '0.25rem' }}>
            ₹{paidPolicies.reduce((sum, p) => sum + p.premium_amount, 0).toLocaleString('en-IN')}
          </div>
        </div>

        <div style={{
          padding: '1rem',
          background: 'var(--white)',
          border: '1.5px solid var(--border)',
          borderRadius: '16px',
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-light)', marginBottom: '0.5rem' }}>
            Unpaid
          </div>
          <div style={{ fontFamily: 'Nunito', fontSize: '1.5rem', fontWeight: 900, color: 'var(--warning)' }}>
            {unpaidPolicies.length}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-mid)', marginTop: '0.25rem' }}>
            ₹{unpaidPolicies.reduce((sum, p) => sum + p.premium_amount, 0).toLocaleString('en-IN')}
          </div>
        </div>

        <div style={{
          padding: '1rem',
          background: 'var(--white)',
          border: '1.5px solid var(--border)',
          borderRadius: '16px',
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-light)', marginBottom: '0.5rem' }}>
            Overdue
          </div>
          <div style={{ fontFamily: 'Nunito', fontSize: '1.5rem', fontWeight: 900, color: 'var(--error)' }}>
            {overduePolicies.length}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-mid)', marginTop: '0.25rem' }}>
            ₹{overduePolicies.reduce((sum, p) => sum + p.premium_amount, 0).toLocaleString('en-IN')}
          </div>
        </div>
      </div>

      {/* Policy table */}
      <div className="proof-table-wrapper">
        <table className="proof-table">
          <thead>
            <tr>
              <th>Policy ID</th>
              <th>Partner</th>
              <th>Tier</th>
              <th>City</th>
              <th>Premium</th>
              <th>Status</th>
              <th>Due Date</th>
            </tr>
          </thead>
          <tbody>
            {filteredPolicies.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-light)' }}>
                  No policies match the selected filters
                </td>
              </tr>
            ) : (
              filteredPolicies.map(policy => {
                const statusColors = {
                  paid: { bg: 'var(--green-light)', color: 'var(--green-dark)' },
                  unpaid: { bg: '#fef9c3', color: '#854d0e' },
                  overdue: { bg: '#fee2e2', color: 'var(--error)' },
                };
                const statusStyle = statusColors[policy.payment_status] || statusColors.unpaid;

                return (
                  <tr key={policy.policy_id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>#{policy.policy_id}</td>
                    <td style={{ fontWeight: 600 }}>{policy.partner_name}</td>
                    <td>
                      <span style={{
                        display: 'inline-block',
                        padding: '0.2rem 0.6rem',
                        borderRadius: '8px',
                        fontSize: '0.7rem',
                        fontWeight: 800,
                        textTransform: 'uppercase',
                        background: 'var(--gray-bg)',
                        color: 'var(--text-mid)',
                      }}>
                        {policy.tier}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>{policy.city}</td>
                    <td style={{ fontWeight: 700, color: 'var(--text-dark)' }}>₹{policy.premium_amount}</td>
                    <td>
                      <span style={{
                        display: 'inline-block',
                        padding: '0.25rem 0.6rem',
                        borderRadius: '8px',
                        fontSize: '0.7rem',
                        fontWeight: 800,
                        textTransform: 'uppercase',
                        background: statusStyle.bg,
                        color: statusStyle.color,
                      }}>
                        {policy.payment_status}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-mid)' }}>
                      {policy.due_date ? new Date(policy.due_date).toLocaleDateString('en-IN') : 'N/A'}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
