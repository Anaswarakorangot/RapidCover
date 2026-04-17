// frontend/src/components/admin/InsurerIntelligencePanel.jsx
// Insurer Intelligence Panel - Predictive analytics and risk management
// Shows zone predictions, city risk profiles, and recommendations

import { useState, useEffect } from 'react';
import { authenticatedFetch } from '../../services/adminApi';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

function riskColor(lr) {
  if (lr > 100) return 'var(--error)';
  if (lr > 85) return '#f97316';
  if (lr > 70) return 'var(--warning)';
  return 'var(--green-primary)';
}

function actionBadge(action) {
  const config = {
    suspend: { bg: '#fee2e2', color: '#991b1b', label: 'SUSPEND' },
    reprice_up: { bg: '#fef3c7', color: '#92400e', label: 'REPRICE UP' },
    reprice_down: { bg: '#d1fae5', color: '#065f46', label: 'REPRICE DOWN' },
    maintain: { bg: '#e0e7ff', color: '#3730a3', label: 'MAINTAIN' },
    monitor: { bg: '#f3f4f6', color: '#374151', label: 'MONITOR' },
  };
  return config[action] || config.maintain;
}

function ProbabilityBar({ label, value, icon }) {
  const pct = Math.min(value * 100, 100);
  return (
    <div style={{ marginBottom: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-mid)', marginBottom: '2px' }}>
        <span>{icon} {label}</span>
        <span>{(value * 100).toFixed(1)}%</span>
      </div>
      <div style={{ height: '6px', background: 'var(--gray-bg)', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          background: pct > 50 ? 'var(--error)' : pct > 25 ? 'var(--warning)' : 'var(--green-primary)',
          borderRadius: '3px',
          transition: 'width 0.3s ease'
        }} />
      </div>
    </div>
  );
}

export default function InsurerIntelligencePanel() {
  const [summary, setSummary] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('summary');

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, profilesRes, predictionsRes] = await Promise.all([
        authenticatedFetch(`${API_BASE}/admin/intelligence/summary`),
        authenticatedFetch(`${API_BASE}/admin/intelligence/risk-profiles`),
        authenticatedFetch(`${API_BASE}/admin/intelligence/predictions`),
      ]);

      if (summaryRes.ok) setSummary(await summaryRes.json());
      if (profilesRes.ok) setProfiles(await profilesRes.json());
      if (predictionsRes.ok) setPredictions(await predictionsRes.json());
    } catch {
      setError('Failed to fetch intelligence data. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await authenticatedFetch(`${API_BASE}/admin/intelligence/refresh`, { method: 'POST' });
      if (res.ok) {
        await fetchData();
      }
    } catch {
      setError('Failed to refresh predictions');
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <section className="intelligence-panel">
        <div style={{ textAlign: 'center', padding: '4rem 0', background: 'var(--gray-bg)', borderRadius: '24px', border: '1.5px solid var(--border)' }}>
          <p style={{ fontFamily: 'Nunito', fontWeight: 800, fontSize: '1.2rem', color: 'var(--text-mid)' }}>Loading intelligence data...</p>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="intelligence-panel">
        <div style={{ textAlign: 'center', padding: '4rem 0', background: '#fef2f2', borderRadius: '24px', border: '1.5px solid var(--error)' }}>
          <p style={{ fontFamily: 'Nunito', fontWeight: 800, fontSize: '1.2rem', color: 'var(--error)' }}>{error}</p>
          <button
            onClick={fetchData}
            style={{ marginTop: '1rem', padding: '0.5rem 1.5rem', borderRadius: '10px', background: 'var(--error)', color: 'white', border: 'none', fontWeight: 700, cursor: 'pointer' }}
          >
            Retry
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="intelligence-panel">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <h2 style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)', margin: 0 }}>
            Insurer Intelligence
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.4rem' }}>
            Predictive analytics and risk management for the upcoming week
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            padding: '0.6rem 1.25rem',
            borderRadius: '12px',
            background: refreshing ? 'var(--text-light)' : 'var(--primary)',
            color: 'white',
            border: 'none',
            fontWeight: 700,
            cursor: refreshing ? 'wait' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          {refreshing ? 'Refreshing...' : 'Refresh Predictions'}
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        {[
          { id: 'summary', label: 'Executive Summary' },
          { id: 'profiles', label: 'City Risk Profiles' },
          { id: 'predictions', label: 'Zone Predictions' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '0.6rem 1.25rem',
              borderRadius: '10px',
              background: activeTab === tab.id ? 'var(--green-primary)' : 'var(--gray-bg)',
              color: activeTab === tab.id ? 'white' : 'var(--text-mid)',
              border: '1.5px solid ' + (activeTab === tab.id ? 'var(--green-primary)' : 'var(--border)'),
              fontWeight: 700,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Summary Tab */}
      {activeTab === 'summary' && summary && (
        <div>
          {/* Alert Cards */}
          {summary.alerts?.length > 0 && (
            <div style={{ marginBottom: '1.5rem' }}>
              {summary.alerts.map((alert, i) => (
                <div
                  key={i}
                  style={{
                    background: alert.level === 'critical' ? '#fee2e2' : '#fef3c7',
                    border: `1.5px solid ${alert.level === 'critical' ? 'var(--error)' : 'var(--warning)'}`,
                    borderRadius: '18px',
                    padding: '1rem 1.25rem',
                    marginBottom: '0.75rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                  }}
                >
                  <span style={{ fontSize: '1.5rem' }}>{alert.level === 'critical' ? '🚨' : '⚠️'}</span>
                  <div>
                    <strong style={{ color: alert.level === 'critical' ? '#991b1b' : '#92400e' }}>{alert.city}</strong>
                    <p style={{ margin: '0.2rem 0 0', fontSize: '0.85rem', color: alert.level === 'critical' ? '#991b1b' : '#92400e' }}>
                      {alert.message}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Stats Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
            {[
              { label: 'Total Cities', value: summary.total_cities, icon: '🏙️' },
              { label: 'At-Risk Cities', value: summary.at_risk_cities?.length || 0, icon: '⚠️', color: 'var(--warning)' },
              { label: 'Predicted Claims', value: summary.total_predicted_claims, icon: '📋' },
              { label: 'Predicted Payout', value: `₹${(summary.total_predicted_payout / 1000).toFixed(1)}K`, icon: '💰' },
            ].map(stat => (
              <div
                key={stat.label}
                style={{
                  background: 'var(--white)',
                  borderRadius: '18px',
                  border: '1.5px solid var(--border)',
                  padding: '1.25rem',
                  textAlign: 'center',
                }}
              >
                <span style={{ fontSize: '1.5rem' }}>{stat.icon}</span>
                <p style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-light)', textTransform: 'uppercase', margin: '0.5rem 0 0.25rem' }}>
                  {stat.label}
                </p>
                <p style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: stat.color || 'var(--text-dark)', margin: 0 }}>
                  {stat.value}
                </p>
              </div>
            ))}
          </div>

          {/* At-Risk Cities List */}
          {summary.at_risk_cities?.length > 0 && (
            <div style={{ background: 'var(--white)', borderRadius: '18px', border: '1.5px solid var(--border)', padding: '1.25rem' }}>
              <h3 style={{ fontFamily: 'Nunito', fontWeight: 800, fontSize: '1rem', color: 'var(--text-dark)', margin: '0 0 1rem' }}>
                Cities Requiring Attention
              </h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {summary.at_risk_cities.map((city, index) => (
                  <span
                    key={`${city}-${index}`}
                    style={{
                      padding: '0.4rem 0.75rem',
                      borderRadius: '8px',
                      background: '#fef3c7',
                      color: '#92400e',
                      fontSize: '0.8rem',
                      fontWeight: 700,
                    }}
                  >
                    {city}
                  </span>
                ))}
              </div>
            </div>
          )}

          {summary.alerts?.length === 0 && summary.at_risk_cities?.length === 0 && (
            <div style={{ background: '#d1fae5', borderRadius: '18px', border: '1.5px solid var(--green-primary)', padding: '2rem', textAlign: 'center' }}>
              <span style={{ fontSize: '2rem' }}>✅</span>
              <p style={{ fontFamily: 'Nunito', fontWeight: 800, fontSize: '1.1rem', color: '#065f46', margin: '0.5rem 0 0' }}>
                All cities healthy - no alerts
              </p>
            </div>
          )}
        </div>
      )}

      {/* Profiles Tab */}
      {activeTab === 'profiles' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1.5rem' }}>
          {profiles.length === 0 ? (
            <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '3rem', background: 'var(--gray-bg)', borderRadius: '24px' }}>
              <p style={{ fontFamily: 'Nunito', fontWeight: 800, color: 'var(--text-mid)' }}>No city profiles yet</p>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-light)' }}>Click "Refresh Predictions" to generate them</p>
            </div>
          ) : (
            profiles.map((profile, index) => {
              const badge = actionBadge(profile.recommendation?.action);
              return (
                <div
                  key={`${profile.city}-${profile.zone_count || index}`}
                  style={{
                    background: 'var(--white)',
                    borderRadius: '24px',
                    border: `1.5px solid ${profile.requires_reinsurance ? 'var(--error)' : profile.is_at_risk ? 'var(--warning)' : 'var(--border)'}`,
                    padding: '1.5rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                    <div>
                      <h3 style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.25rem', margin: 0 }}>{profile.city}</h3>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-light)' }}>
                        Confidence: {(profile.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <span
                      style={{
                        padding: '0.3rem 0.6rem',
                        borderRadius: '8px',
                        background: badge.bg,
                        color: badge.color,
                        fontSize: '0.65rem',
                        fontWeight: 800,
                      }}
                    >
                      {badge.label}
                    </span>
                  </div>

                  {/* Loss Ratio Comparison */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                    <div style={{ background: 'var(--gray-bg)', borderRadius: '12px', padding: '0.75rem', textAlign: 'center' }}>
                      <p style={{ fontSize: '0.65rem', color: 'var(--text-light)', fontWeight: 700, margin: 0 }}>CURRENT LR</p>
                      <p style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.25rem', color: riskColor(profile.current_loss_ratio), margin: '0.25rem 0 0' }}>
                        {profile.current_loss_ratio}%
                      </p>
                    </div>
                    <div style={{ background: 'var(--gray-bg)', borderRadius: '12px', padding: '0.75rem', textAlign: 'center' }}>
                      <p style={{ fontSize: '0.65rem', color: 'var(--text-light)', fontWeight: 700, margin: 0 }}>PREDICTED LR</p>
                      <p style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.25rem', color: riskColor(profile.predicted_loss_ratio), margin: '0.25rem 0 0' }}>
                        {profile.predicted_loss_ratio}%
                      </p>
                    </div>
                  </div>

                  {/* Stats */}
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-mid)', marginBottom: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                      <span>Premiums (7d):</span>
                      <strong>₹{(profile.total_premiums_7d / 1000).toFixed(1)}K</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                      <span>Payouts (7d):</span>
                      <strong>₹{(profile.total_payouts_7d / 1000).toFixed(1)}K</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Predicted Claims:</span>
                      <strong>{profile.predicted_claims}</strong>
                    </div>
                  </div>

                  {/* Recommendation */}
                  {profile.recommendation?.reason && (
                    <div style={{ background: badge.bg + '50', borderRadius: '10px', padding: '0.75rem', fontSize: '0.8rem', color: badge.color }}>
                      {profile.recommendation.reason}
                      {profile.recommendation.premium_adjustment && (
                        <strong style={{ display: 'block', marginTop: '0.25rem' }}>
                          Suggested adjustment: {profile.recommendation.premium_adjustment > 0 ? '+' : ''}{profile.recommendation.premium_adjustment}%
                        </strong>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Predictions Tab */}
      {activeTab === 'predictions' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
          {predictions.length === 0 ? (
            <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '3rem', background: 'var(--gray-bg)', borderRadius: '24px' }}>
              <p style={{ fontFamily: 'Nunito', fontWeight: 800, color: 'var(--text-mid)' }}>No zone predictions yet</p>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-light)' }}>Click "Refresh Predictions" to generate them</p>
            </div>
          ) : (
            predictions.map(pred => (
              <div
                key={pred.zone_id}
                style={{
                  background: 'var(--white)',
                  borderRadius: '18px',
                  border: '1.5px solid var(--border)',
                  padding: '1.25rem',
                }}
              >
                <div style={{ marginBottom: '1rem' }}>
                  <h4 style={{ fontFamily: 'Nunito', fontWeight: 800, fontSize: '1rem', margin: 0 }}>{pred.zone_name}</h4>
                  <code style={{ fontSize: '0.7rem', color: 'var(--text-light)' }}>{pred.zone_code}</code>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-light)', marginLeft: '0.5rem' }}>· {pred.city}</span>
                </div>

                {/* Trigger Probabilities */}
                <div style={{ marginBottom: '1rem' }}>
                  <ProbabilityBar label="Rain/Flood" value={pred.probabilities.rain} icon="🌧️" />
                  <ProbabilityBar label="Heat" value={pred.probabilities.heat} icon="🌡️" />
                  <ProbabilityBar label="AQI" value={pred.probabilities.aqi} icon="💨" />
                  <ProbabilityBar label="Shutdown" value={pred.probabilities.shutdown} icon="🚨" />
                  <ProbabilityBar label="Closure" value={pred.probabilities.closure} icon="🏪" />
                </div>

                {/* Expected Outcomes */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', fontSize: '0.75rem' }}>
                  <div style={{ background: 'var(--gray-bg)', borderRadius: '8px', padding: '0.5rem', textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-light)', fontSize: '0.6rem', fontWeight: 700 }}>TRIGGERS</div>
                    <div style={{ fontWeight: 800 }}>{pred.expected_triggers}</div>
                  </div>
                  <div style={{ background: 'var(--gray-bg)', borderRadius: '8px', padding: '0.5rem', textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-light)', fontSize: '0.6rem', fontWeight: 700 }}>CLAIMS</div>
                    <div style={{ fontWeight: 800 }}>{pred.expected_claims}</div>
                  </div>
                  <div style={{ background: 'var(--gray-bg)', borderRadius: '8px', padding: '0.5rem', textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-light)', fontSize: '0.6rem', fontWeight: 700 }}>LOSS RATIO</div>
                    <div style={{ fontWeight: 800, color: riskColor(pred.expected_loss_ratio) }}>{pred.expected_loss_ratio}%</div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </section>
  );
}
