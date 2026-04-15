import { useEffect, useState, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export default function AdminStats({ stats }) {
  const [animated, setAnimated] = useState(false);
  const [selectedZone, setSelectedZone] = useState(0); // index into zoneLossRatios
  const [liveData, setLiveData] = useState(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [zones, setZones] = useState([]);
  const [selectedLiveZone, setSelectedLiveZone] = useState('');

  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 100);
    return () => clearTimeout(t);
  }, []);

  const fetchLiveData = useCallback(async (zoneCode) => {
    const code = zoneCode || selectedLiveZone;
    if (!code) return;
    setLiveLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/panel/live-data?zone_code=${code}`);
      if (res.ok) {
        setLiveData(await res.json());
      }
    } catch (_err) {
      console.error('Failed to fetch live data:', _err);
    }
    setLiveLoading(false);
  }, [selectedLiveZone]);

  useEffect(() => {
    const fetchZones = async () => {
      try {
        const res = await fetch(`${API_BASE}/zones`);
        if (res.ok) {
          const list = await res.json();
          setZones(list);
          if (list.length > 0) {
            setSelectedLiveZone(list[0].code);
            fetchLiveData(list[0].code);
          }
        }
      } catch (_err) {
        console.error('Failed to fetch zones:', _err);
      }
    };
    fetchZones();
  }, [fetchLiveData]);

  if (!stats) return null;

  // Fix 6 — 8th card: Premium collected this week
  const premiumCollected = stats.totalPremiumsRs
    || Math.round(stats.totalPayoutsRs / ((stats.lossRatioPercent || 63) / 100));

  const statCards = [
    { label: 'Active Policies', value: stats.activePolicies?.toLocaleString('en-IN'), color: 'var(--green-primary)', pct: 85 },
    { label: 'Claims This Week', value: stats.claimsThisWeek, color: 'var(--text-mid)', pct: 45 },
    { label: 'Total Payouts', value: `₹${(stats.totalPayoutsRs / 1000).toFixed(1)}K`, color: 'var(--text-dark)', pct: 62 },
    { label: 'Loss Ratio', value: `${stats.lossRatioPercent}%`, color: stats.lossRatioPercent > 75 ? 'var(--error)' : 'var(--green-primary)', pct: stats.lossRatioPercent },
    { label: 'Auto-Approval Rate', value: `${stats.autoApprovalRate}%`, color: 'var(--text-mid)', pct: stats.autoApprovalRate },
    { label: 'Fraud Queue', value: `${stats.fraudQueueCount} flagged`, color: 'var(--warning)', pct: 20 },
    { label: 'Avg Payout Time', value: `${stats.avgPayoutMinutes} min`, color: 'var(--text-mid)', pct: 90 },
    { label: 'Premium Collected', value: `₹${(premiumCollected / 1000).toFixed(1)}K`, color: 'var(--green-primary)', pct: 78 },
  ];

  // Zone loss ratios with dropdown selector
  const zoneLRs = stats.zoneLossRatios || [];
  const activeZone = zoneLRs[selectedZone] || zoneLRs[0] || { zone: 'No zones', zone_code: 'N/A', lr: 0 };

  return (
    <div className="admin-section" style={{ animationDelay: '0.1s' }}>
      <div className="admin-section-label">PLATFORM HEALTH</div>

      {/* Stats grid — 4 columns × 2 rows */}
      <div className="stats-grid">
        {statCards.map((s, i) => (
            <div 
              key={s.label} 
              className={`stat-card ${animated ? 'stat-card--visible' : ''}`}
              style={{ transitionDelay: `${i * 60}ms` }}
            >
              <span className="stat-card__label">{s.label}</span>
              <span className="stat-card__value" style={{ color: s.color }}>{s.value}</span>
              <div className="lr-mini-bar">
                <div 
                  className="lr-mini-fill" 
                  style={{ 
                    width: `${s.pct}%`, 
                    background: s.label.includes('Ratio') && s.pct > 75 ? 'var(--error)' : 'var(--green-primary)' 
                  }} 
                />
              </div>
            </div>
        ))}
      </div>

      {/* Loss ratio bar with zone selector */}
      <div className="loss-ratio-bar">
        <div className="loss-ratio-bar__header" style={{ marginBottom: '1rem' }}>
          <div className="loss-ratio-bar__zone-selector">
            <span className="loss-ratio-bar__title" style={{ fontFamily: 'Nunito', fontWeight: 800 }}>Zone loss ratio</span>
            {zoneLRs.length > 1 && (
              <select
                className="loss-ratio-zone-select"
                value={selectedZone}
                onChange={e => setSelectedZone(Number(e.target.value))}
                style={{ border: '1.5px solid var(--border)', borderRadius: '10px', padding: '0.4rem 0.75rem', background: 'var(--white)', fontFamily: 'DM Sans', fontWeight: 600 }}
              >
                {zoneLRs.map((z, i) => (
                  <option key={z.zone_code} value={i}>
                    {z.zone_code} — {z.zone}
                  </option>
                ))}
              </select>
            )}
          </div>
          <span 
            className="loss-ratio-bar__value" 
            style={{ 
              fontFamily: 'Nunito',
              fontWeight: 900,
              fontSize: '1.1rem',
              color: activeZone.lr >= 80 ? 'var(--error)' : 'var(--green-primary)' 
            }}
          >
            {activeZone.lr}% — {activeZone.lr >= 80 ? 'REPRICE REQUIRED' : 'HEALTHY'}
          </span>
        </div>
        <div className="loss-ratio-bar__track" style={{ height: '14px', background: 'var(--green-light)' }}>
          <div 
            className="loss-ratio-bar__fill" 
            style={{ 
              width: animated ? `${Math.min(activeZone.lr, 100)}%` : '0%',
              background: activeZone.lr >= 80 
                ? 'var(--error)'
                : 'var(--green-primary)',
              boxShadow: 'none'
            }} 
          />
          <div className="loss-ratio-bar__threshold" style={{ left: '80%', height: '22px', background: 'var(--warning)', width: '3px', top: '-4px' }} />
        </div>
        <div className="loss-ratio-bar__labels" style={{ marginTop: '0.75rem', fontWeight: 600 }}>
          <span>0%</span>
          <span className="loss-ratio-bar__threshold-label" style={{ left: '80%', color: 'var(--warning)', fontWeight: 800 }}>80% threshold</span>
          <span>100%</span>
        </div>
      </div>

      {/* Live API Data Card */}
      <div className="admin-section-label" style={{ marginTop: '2rem' }}>LIVE API DATA</div>
      <div style={{
        background: 'var(--white)',
        borderRadius: '18px',
        border: '1.5px solid var(--border)',
        padding: '1.25rem',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.5rem' }}>📡</span>
            <div>
              <div style={{ fontWeight: 800, fontSize: '1rem', color: 'var(--text-dark)' }}>External API Status</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-light)' }}>Weather, AQI, Platform data</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <select
              value={selectedLiveZone}
              onChange={(e) => {
                setSelectedLiveZone(e.target.value);
                fetchLiveData(e.target.value);
              }}
              style={{
                padding: '0.5rem',
                borderRadius: '8px',
                border: '1.5px solid var(--border)',
                fontSize: '0.8rem',
                fontWeight: 600,
              }}
            >
              {zones.map(z => (
                <option key={z.code} value={z.code}>{z.code}</option>
              ))}
            </select>
            <button
              onClick={() => fetchLiveData()}
              disabled={liveLoading}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '8px',
                background: liveLoading ? 'var(--text-light)' : 'var(--primary)',
                color: 'white',
                border: 'none',
                fontWeight: 700,
                fontSize: '0.85rem',
                cursor: liveLoading ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
              }}
            >
              {liveLoading ? '...' : '🔄 Fetch'}
            </button>
          </div>
        </div>

        {liveData && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
            {/* Weather */}
            <div style={{ padding: '0.75rem', background: 'var(--bg-light)', borderRadius: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>🌤️ Weather</span>
                <span style={{
                  padding: '2px 6px',
                  borderRadius: '8px',
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  background: liveData.weather?.source === 'live' ? '#22c55e20' : '#f59e0b20',
                  color: liveData.weather?.source === 'live' ? '#22c55e' : '#f59e0b',
                }}>{liveData.weather?.source?.toUpperCase()}</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-mid)' }}>
                <div>🌡️ {liveData.weather?.temp_celsius}°C</div>
                <div>🌧️ {liveData.weather?.rainfall_mm_hr} mm/hr</div>
                <div>💧 {liveData.weather?.humidity}%</div>
              </div>
            </div>

            {/* AQI */}
            <div style={{ padding: '0.75rem', background: 'var(--bg-light)', borderRadius: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>💨 AQI</span>
                <span style={{
                  padding: '2px 6px',
                  borderRadius: '8px',
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  background: liveData.aqi?.source === 'live' ? '#22c55e20' : '#f59e0b20',
                  color: liveData.aqi?.source === 'live' ? '#22c55e' : '#f59e0b',
                }}>{liveData.aqi?.source?.toUpperCase()}</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-mid)' }}>
                <div>AQI: <strong>{liveData.aqi?.aqi}</strong></div>
                <div>PM2.5: {liveData.aqi?.pm25}</div>
                <div>{liveData.aqi?.category}</div>
              </div>
            </div>

            {/* Platform */}
            <div style={{ padding: '0.75rem', background: 'var(--bg-light)', borderRadius: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>🏪 Platform</span>
                <span style={{
                  padding: '2px 6px',
                  borderRadius: '8px',
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  background: '#f59e0b20',
                  color: '#f59e0b',
                }}>MOCK</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-mid)' }}>
                <div>{liveData.platform?.is_open ? '✅ Store Open' : '❌ Closed'}</div>
                {liveData.platform?.closure_reason && (
                  <div style={{ fontSize: '0.7rem' }}>{liveData.platform.closure_reason}</div>
                )}
              </div>
            </div>

            {/* Shutdown */}
            <div style={{ padding: '0.75rem', background: 'var(--bg-light)', borderRadius: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>🚨 Civic</span>
                <span style={{
                  padding: '2px 6px',
                  borderRadius: '8px',
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  background: '#f59e0b20',
                  color: '#f59e0b',
                }}>MOCK</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-mid)' }}>
                <div>{liveData.shutdown?.is_active ? '⚠️ Shutdown Active' : '✅ Normal'}</div>
                {liveData.shutdown?.reason && (
                  <div style={{ fontSize: '0.7rem' }}>{liveData.shutdown.reason}</div>
                )}
              </div>
            </div>
          </div>
        )}

        {!liveData && !liveLoading && (
          <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-light)' }}>
            Click "Fetch" to load live API data
          </div>
        )}
      </div>
    </div>
  );
}
