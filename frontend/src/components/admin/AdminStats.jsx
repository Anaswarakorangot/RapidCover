import { useEffect, useState, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export default function AdminStats({ stats }) {
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState(0); // index into zoneLossRatios
  const [selectedLiveZone, setSelectedLiveZone] = useState('');


  const fetchLiveData = useCallback(async (zoneCode) => {
    const code = zoneCode || selectedLiveZone;
    if (!code) return;
    try {
      await fetch(`${API_BASE}/admin/panel/live-data?zone_code=${code}`);
      // In a real app we'd set state here, but for now we just verify connectivity
    } catch (_err) {
      console.error('Failed to fetch live data:', _err);
    }
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

  // Map RapidCover data to localized concepts
  const premiumCollected = stats.totalPremiumsRs || 0;
  const activePolicies = stats.activePolicies || 0;
  const totalPayouts = stats.totalPayoutsRs || 0;
  const lossRatio = stats.lossRatioPercent || 0;

  const mainKPIs = [
    { label: 'Premium Collected', value: `₹${(premiumCollected / 1000).toFixed(1)}K`, icon: '💰', color: '#f7b924', sub: '-5.1% loss earnings' },
    { label: 'Active Policies', value: activePolicies.toLocaleString('en-IN'), icon: '📝', color: '#d92550', sub: 'Grow Rate: 14.1%' },
    { label: 'Total Payouts', value: `₹${(totalPayouts / 1000).toFixed(1)}K`, icon: '💸', color: '#3ac47d', sub: 'Increased by 7.35%' },
  ];

  const miniStats = [
    { label: 'Claims This Week', value: stats.claimsThisWeek, color: 'var(--primary)' },
    { label: 'Auto-Approval Rate', value: `${stats.autoApprovalRate}%`, color: 'var(--success)' },
    { label: 'Fraud Queue', value: stats.fraudQueueCount, color: 'var(--danger)' },
    { label: 'Avg Payout Time', value: `${stats.avgPayoutMinutes}m`, color: 'var(--info)' },
  ];

  return (
    <div className="admin-stats-rapidcover">
      {/* Top 3 Large Card Section */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '2rem' }}>
        {mainKPIs.map((kpi, i) => (
          <div key={i} className="rapidcover-stat-card" style={{ borderLeft: `5px solid ${kpi.color}`, padding: '1.5rem', background: 'white', boxShadow: 'var(--premium-shadow)', borderRadius: 'var(--card-radius)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase' }}>{kpi.label}</div>
                <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--text-dark)', margin: '0.5rem 0' }}>{kpi.value}</div>
                <div style={{ fontSize: '0.8rem', color: kpi.sub.includes('-') ? 'var(--danger)' : 'var(--success)', fontWeight: 700 }}>{kpi.sub}</div>
              </div>
              <div style={{ fontSize: '2rem', opacity: 0.2 }}>{kpi.icon}</div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ width: '100%', textAlign: 'center', marginBottom: '2rem' }}>
        <button className="menu-item--active" style={{ padding: '0.5rem 2rem', borderRadius: '30px', border: 'none', cursor: 'pointer', fontWeight: 700 }}>
          View Complete Report
        </button>
      </div>

      {/* Middle Split: Chart and Timeline */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.25fr) minmax(0, 0.75fr)', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Loss Ratio Area Chart */}
        <div className="architect-card" style={{ background: 'white', padding: '1.5rem', boxShadow: 'var(--premium-shadow)', borderRadius: 'var(--card-radius)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '1rem' }}>
            <div style={{ fontWeight: 800, color: 'var(--text-dark)' }}>📊 Loss Ratio Performance</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--primary)', cursor: 'pointer', fontWeight: 700 }}>VIEW ALL</div>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
             <div>
                <div style={{ fontSize: '2.5rem', fontWeight: 900, color: lossRatio > 80 ? 'var(--danger)' : 'var(--success)' }}>{lossRatio}%</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Current Loss Ratio</div>
                <div style={{ color: 'var(--success)', fontSize: '0.8rem', fontWeight: 700, marginTop: '0.2rem' }}>↑ 14 pts healthy</div>
             </div>
             {/* Mock SVG Chart to mimic the Area look */}
             <div style={{ flex: 1, height: '120px' }}>
                <svg width="100%" height="100%" viewBox="0 0 100 30" preserveAspectRatio="none">
                  <path d="M0 30 L0 10 Q 25 5, 50 15 T 100 10 L 100 30 Z" fill="rgba(58, 196, 125, 0.1)" stroke="var(--success)" strokeWidth="1" />
                  <circle cx="20" cy="8" r="1.5" fill="var(--success)" />
                  <circle cx="50" cy="15" r="1.5" fill="var(--success)" />
                  <circle cx="80" cy="12" r="1.5" fill="var(--success)" />
                </svg>
             </div>
          </div>
        </div>

        {/* System Activity Timeline */}
        <div className="architect-card" style={{ background: 'white', padding: '1.5rem', boxShadow: 'var(--premium-shadow)', borderRadius: 'var(--card-radius)' }}>
           <div style={{ fontWeight: 800, color: 'var(--text-dark)', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '1rem' }}>
             🕒 System Activity
           </div>
           <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--danger)', marginTop: '4px' }} />
                <div style={{ fontSize: '0.85rem' }}>
                  <div style={{ fontWeight: 700 }}>Trigger Poll Completed</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Just now · Central Zone</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--warning)', marginTop: '4px' }} />
                <div style={{ fontSize: '0.85rem' }}>
                  <div style={{ fontWeight: 700 }}>New Claim Flagged</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>5 mins ago · Speed Fraud</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--success)', marginTop: '4px' }} />
                <div style={{ fontSize: '0.85rem' }}>
                  <div style={{ fontWeight: 700 }}>Payout Batch Finished</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>1 hour ago · 14 payments</div>
                </div>
              </div>
           </div>
           <button style={{ width: '100%', marginTop: '1.5rem', padding: '0.5rem', borderRadius: '6px', background: 'var(--text-dark)', color: 'white', border: 'none', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer' }}>
             View All Messages
           </button>
        </div>
      </div>

      {/* Bottom Mini Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem' }}>
        {miniStats.map((ms, i) => (
          <div key={i} className="architect-card" style={{ background: 'white', padding: '1.25rem', textAlign: 'center', boxShadow: 'var(--premium-shadow)', borderRadius: 'var(--card-radius)' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: ms.color }}>{ms.value}</div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginTop: '0.2rem', textTransform: 'uppercase' }}>{ms.label}</div>
          </div>
        ))}
      </div>

      {/* Zone Selector and Live API Data (Moved to bottom) */}
      <div style={{ marginTop: '2rem' }}>
        <div className="architect-card" style={{ background: 'white', padding: '1.5rem', boxShadow: 'var(--premium-shadow)', borderRadius: 'var(--card-radius)' }}>
           <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
             <div style={{ fontWeight: 800 }}>Global Status Selector</div>
             <select
                  className="loss-ratio-zone-select"
                  value={selectedZone}
                  onChange={e => setSelectedZone(Number(e.target.value))}
                  style={{ border: '1px solid var(--border-light)', borderRadius: '6px', padding: '0.5rem' }}
                >
                  {stats.zoneLossRatios?.map((z, i) => (
                    <option key={z.zone_code} value={i}>{z.zone_code} — {z.zone}</option>
                  ))}
            </select>
           </div>
           <div style={{ height: '10px', background: '#f1f4f6', borderRadius: '10px', overflow: 'hidden' }}>
              <div style={{ width: `${stats.zoneLossRatios?.[selectedZone]?.lr || 0}%`, height: '100%', background: 'var(--primary)', transition: 'width 1s' }} />
           </div>
        </div>
      </div>
    </div>
  );
}

