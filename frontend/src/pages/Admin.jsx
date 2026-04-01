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

  useEffect(() => {
    loadStats();
  }, []);

  async function loadStats() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/panel/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      } else {
        // Fallback demo data
        setStats(demoStats);
      }
    } catch {
      setStats(demoStats);
    } finally {
      setLoading(false);
    }
  }

  const today = new Date().toLocaleDateString('en-IN', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

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
          <span className="admin-status__dot" />
          All systems operational
        </div>
      </header>

      {/* Platform Health Stats */}
      <AdminStats stats={stats} />

      {/* Trigger Simulation */}
      <TriggerPanel />

      {/* Fraud Review Queue */}
      <ClaimsQueue />

      {/* Coverage Exclusions */}
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
