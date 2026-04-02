import { useEffect, useState } from 'react';

export default function AdminStats({ stats }) {
  const [animated, setAnimated] = useState(false);
  const [selectedZone, setSelectedZone] = useState(0); // index into zoneLossRatios

  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 100);
    return () => clearTimeout(t);
  }, []);

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
  const activeZone = zoneLRs[selectedZone] || zoneLRs[0] || { zone_code: 'BLR-047', lr: 71 };

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
    </div>
  );
}
