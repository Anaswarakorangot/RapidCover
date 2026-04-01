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
    { label: 'Active Policies', value: stats.activePolicies?.toLocaleString('en-IN'), color: '#d4a24e' },
    { label: 'Claims This Week', value: stats.claimsThisWeek, color: '#a3a3a3' },
    { label: 'Total Payouts', value: `₹${(stats.totalPayoutsRs / 1000).toFixed(1)}K`, color: '#5eead4' },
    { label: 'Loss Ratio', value: `${stats.lossRatioPercent}%`, color: stats.lossRatioPercent > 75 ? '#ef4444' : '#d4a24e' },
    { label: 'Auto-Approval Rate', value: `${stats.autoApprovalRate}%`, color: '#a3a3a3' },
    { label: 'Fraud Queue', value: `${stats.fraudQueueCount} flagged`, color: '#f97316' },
    { label: 'Avg Payout Time', value: `${stats.avgPayoutMinutes} min`, color: '#a3a3a3' },
    { label: 'Premium Collected', value: `₹${(premiumCollected / 1000).toFixed(1)}K`, color: '#22c55e' },
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
          </div>
        ))}
      </div>

      {/* Loss ratio bar with zone selector */}
      <div className="loss-ratio-bar">
        <div className="loss-ratio-bar__header">
          <div className="loss-ratio-bar__zone-selector">
            <span className="loss-ratio-bar__title">Loss ratio this week</span>
            {zoneLRs.length > 1 && (
              <select
                className="loss-ratio-zone-select"
                value={selectedZone}
                onChange={e => setSelectedZone(Number(e.target.value))}
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
            style={{ color: activeZone.lr >= 80 ? '#ef4444' : '#d4a24e' }}
          >
            {activeZone.lr}% — {activeZone.lr >= 80 ? 'reprice!' : 'watch'}
          </span>
        </div>
        <div className="loss-ratio-bar__track">
          <div
            className="loss-ratio-bar__fill"
            style={{
              width: animated ? `${Math.min(activeZone.lr, 100)}%` : '0%',
              background: activeZone.lr >= 80
                ? 'linear-gradient(90deg, #f97316, #ef4444)'
                : 'linear-gradient(90deg, #d4a24e, #f97316)',
            }}
          />
          {/* Fix 4 — 80% threshold as actual vertical line */}
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
