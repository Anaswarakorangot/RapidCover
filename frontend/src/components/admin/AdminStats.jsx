import { useEffect, useState } from 'react';

export default function AdminStats({ stats }) {
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 100);
    return () => clearTimeout(t);
  }, []);

  if (!stats) return null;

  const statCards = [
    { label: 'Active policies', value: stats.activePolicies?.toLocaleString('en-IN'), color: '#d4a24e' },
    { label: 'Claims this week', value: stats.claimsThisWeek, color: '#a3a3a3' },
    { label: 'Total payouts', value: `₹${(stats.totalPayoutsRs / 1000).toFixed(1)}K`, color: '#5eead4' },
    { label: 'Loss ratio', value: `${stats.lossRatioPercent}%`, color: stats.lossRatioPercent > 75 ? '#ef4444' : '#d4a24e' },
    { label: 'Auto-approval rate', value: `${stats.autoApprovalRate}%`, color: '#a3a3a3' },
    { label: 'Fraud queue', value: `${stats.fraudQueueCount} flagged`, color: '#f97316' },
    { label: 'Avg payout time', value: `${stats.avgPayoutMinutes} min`, color: '#a3a3a3' },
  ];

  // Find the worst zone LR for the bar
  const zoneLRs = stats.zoneLossRatios || [];
  const worstZone = zoneLRs.length > 0
    ? zoneLRs.reduce((a, b) => a.lr > b.lr ? a : b)
    : { zone_code: 'BLR-047', lr: 71 };

  return (
    <div className="admin-section" style={{ animationDelay: '0.1s' }}>
      <div className="admin-section-label">ADMINSTATS.JSX — PLATFORM HEALTH</div>

      {/* Stats grid */}
      <div className="stats-grid">
        {statCards.map((s, i) => (
          <div
            key={s.label}
            className={`stat-card ${animated ? 'stat-card--visible' : ''}`}
            style={{ transitionDelay: `${i * 60}ms` }}
          >
            <span className="stat-card__label">{s.label}</span>
            <span className="stat-card__value" style={{ color: s.color }}>{s.value}</span>
          </div>
        ))}
      </div>

      {/* Loss ratio bar */}
      <div className="loss-ratio-bar">
        <div className="loss-ratio-bar__header">
          <span className="loss-ratio-bar__title">
            Zone {worstZone.zone_code} loss ratio this week
          </span>
          <span
            className="loss-ratio-bar__value"
            style={{ color: worstZone.lr >= 80 ? '#ef4444' : '#d4a24e' }}
          >
            {worstZone.lr}% — {worstZone.lr >= 80 ? 'reprice!' : 'watch'}
          </span>
        </div>
        <div className="loss-ratio-bar__track">
          <div
            className="loss-ratio-bar__fill"
            style={{
              width: animated ? `${Math.min(worstZone.lr, 100)}%` : '0%',
              background: worstZone.lr >= 80
                ? 'linear-gradient(90deg, #f97316, #ef4444)'
                : 'linear-gradient(90deg, #d4a24e, #f97316)',
            }}
          />
          {/* 80% threshold marker */}
          <div className="loss-ratio-bar__threshold" style={{ left: '80%' }} />
        </div>
        <div className="loss-ratio-bar__labels">
          <span>0%</span>
          <span className="loss-ratio-bar__threshold-label" style={{ left: '80%' }}>
            80% threshold
          </span>
          <span>100%</span>
        </div>
      </div>
    </div>
  );
}
