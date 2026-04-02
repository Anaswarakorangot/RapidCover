import { useState, useEffect } from 'react';
import AdminStats from '../components/admin/AdminStats';
import TriggerPanel from '../components/admin/TriggerPanel';
import ClaimsQueue from '../components/admin/ClaimsQueue';
import ExclusionsCard from '../components/admin/ExclusionsCard';
import './Admin.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export function Admin() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [systemStatus, setSystemStatus] = useState({ level: 'green', text: 'All systems operational' });

  useEffect(() => {
    loadStats();
    checkSystemStatus();
    const statusInterval = setInterval(checkSystemStatus, 15000);
    return () => clearInterval(statusInterval);
  }, []);

  async function loadStats() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/panel/stats`);
      if (res.ok) {
        setStats(await res.json());
      } else {
        setStats(demoStats);
      }
    } catch {
      setStats(demoStats);
    } finally {
      setLoading(false);
    }
  }

  // Fix: wire system status badge to real engine state
  async function checkSystemStatus() {
    try {
      const res = await fetch(`${API_BASE}/admin/panel/engine-status`);
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();

      const schedulerRunning = data.scheduler?.running;
      const sources = data.data_sources || {};

      // Only check real data sources (OWM, WAQI) — Zepto/Traffic/Civic are always mock
      const realSources = ['openweathermap', 'waqi_aqi'];
      const anyRealLive = realSources.some(k => sources[k]?.status === 'live');

      if (!schedulerRunning) {
        setSystemStatus({ level: 'red', text: 'Scheduler stopped' });
      } else if (anyRealLive) {
        setSystemStatus({ level: 'green', text: 'All systems operational' });
      } else {
        setSystemStatus({ level: 'amber', text: 'Running on mock data' });
      }
    } catch {
      setSystemStatus({ level: 'red', text: 'Backend unreachable' });
    }
  }

  const today = new Date().toLocaleDateString('en-IN', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  const statusDotClass =
    systemStatus.level === 'green' ? 'admin-status__dot--green'
    : systemStatus.level === 'amber' ? 'admin-status__dot--amber'
    : 'admin-status__dot--red';

  if (loading) {
    return (
      <div className="admin-root">
        <div className="admin-loader">
          <div className="admin-loader__spinner" />
          <span>Loading control panel…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-root">
      {/* Header */}
      <header className="admin-header">
        <div>
          <h1 className="admin-title">Admin control panel</h1>
          <p className="admin-subtitle">RapidCover · Live · {today}</p>
        </div>
        <div className="admin-status">
          <span className={`admin-status__dot ${statusDotClass}`} />
          {systemStatus.text}
        </div>
      </header>

      <AdminStats stats={stats} />
      <TriggerPanel />
      <ClaimsQueue />
      <ExclusionsCard />
    </div>
  );
}

// Demo fallback data
const demoStats = {
  activePolicies: 1247,
  claimsThisWeek: 83,
  totalPayoutsRs: 31500,
  lossRatioPercent: 63,
  autoApprovalRate: 89,
  fraudQueueCount: 6,
  avgPayoutMinutes: 8.2,
  zoneLossRatios: [
    { zone: 'Koramangala', zone_code: 'BLR-047', lr: 71 },
    { zone: 'Andheri East', zone_code: 'MUM-021', lr: 54 },
    { zone: 'Connaught Place', zone_code: 'DEL-009', lr: 48 },
  ],
};
