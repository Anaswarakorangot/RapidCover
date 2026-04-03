// frontend/src/pages/Admin.jsx
// Person 4 — fully updated admin dashboard
// Adds: BCRPanel, StressWidget, ZoneMapPanel, FraudQueuePanel, MLStatusPanel
// Phase 2: DrillPanel, VerificationPanel
// Keeps: AdminStats, TriggerPanel, ExclusionsCard (untouched — don't break what works)

import { useState, useEffect, useRef } from 'react';
import AdminStats    from '../components/admin/AdminStats';
import TriggerPanel  from '../components/admin/TriggerPanel';
import ExclusionsCard from '../components/admin/ExclusionsCard';
import BCRPanel      from '../components/admin/BCRPanel';
import ZoneMapPanel  from '../components/admin/ZoneMapPanel';
import FraudQueuePanel from '../components/admin/FraudQueuePanel';
import MLStatusPanel from '../components/admin/MLStatusPanel';
import DrillPanel    from '../components/admin/DrillPanel';
import VerificationPanel from '../components/admin/VerificationPanel';
import StressProofPanel from '../components/admin/StressProofPanel';
import ReassignmentQueuePanel from '../components/admin/ReassignmentQueuePanel';
import TriggerProofPanel from '../components/admin/TriggerProofPanel';
import RiqiProvenancePanel from '../components/admin/RiqiProvenancePanel';
import NotificationPreviewPanel from '../components/admin/NotificationPreviewPanel';
import DemoChecklist from '../components/admin/DemoChecklist';
import './Admin.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export function Admin() {
  const [stats, setStats]           = useState(null);
  const [loading, setLoading]       = useState(true);
  const [activeTab, setActiveTab]   = useState('overview');
  const [systemStatus, setSystemStatus] = useState({ level: 'green', text: 'All systems operational' });
  const drillZoneSelectRef = useRef(null);

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
      setStats(res.ok ? await res.json() : demoStats);
    } catch {
      setStats(demoStats);
    } finally {
      setLoading(false);
    }
  }

  async function checkSystemStatus() {
    try {
      const res = await fetch(`${API_BASE}/admin/panel/engine-status`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      const schedulerRunning = data.scheduler?.running;
      const sources = data.data_sources || {};
      const realSources = ['openweathermap', 'waqi_aqi'];
      const anyRealLive = realSources.some(k => sources[k]?.status === 'live');

      if (!schedulerRunning)      setSystemStatus({ level: 'red',   text: 'Scheduler stopped' });
      else if (anyRealLive)       setSystemStatus({ level: 'green', text: 'All systems operational' });
      else                        setSystemStatus({ level: 'amber', text: 'Running on mock data' });
    } catch {
      setSystemStatus({ level: 'red', text: 'Backend unreachable' });
    }
  }

  const today = new Date().toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' });

  const statusDotClass =
    systemStatus.level === 'green' ? 'admin-status__dot--green'
    : systemStatus.level === 'amber' ? 'admin-status__dot--amber'
    : 'admin-status__dot--red';

  const TABS = [
    { id: 'overview',        label: '\u{1F4CA} Overview' },
    { id: 'bcr',             label: '\u{1F4C9} BCR / Loss Ratio' },
    { id: 'map',             label: '\u{1F5FA} Zone Map' },
    { id: 'fraud',           label: '\u{1F50D} Fraud Queue' },
    { id: 'drills',          label: '\u{1F3AF} Drills' },
    { id: 'verify',          label: '\u{1F50D} Verification' },
    { id: 'stress',          label: '\u26A1 Stress Proof' },
    { id: 'reassign',        label: '\u{1F504} Reassignments' },
    { id: 'trigger-proof',   label: '\u{1F3AF} Trigger Proof' },
    { id: 'riqi',            label: '\u{1F4CA} RIQI Provenance' },
    { id: 'notif-preview',   label: '\u{1F514} Notifications' },
    { id: 'ml',              label: '\u{1F916} ML Models' },
    { id: 'checklist',       label: '\u2705 Demo Checklist' },
    { id: 'triggers',        label: '\u{2699}\u{FE0F} Legacy Sim' },
  ];

  // Handle zone selection from map to drill panel
  function handleMapZoneClick(zoneCode) {
    if (drillZoneSelectRef.current) {
      drillZoneSelectRef.current(zoneCode);
      setActiveTab('drills');
    }
  }

  if (loading) {
    return (
      <div className="admin-root">
        <div className="admin-loader">
          <div className="admin-loader__spinner" />
          <span>Loading control panel...</span>
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

      {/* Tab nav */}
      <nav className="admin-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`admin-tab ${activeTab === t.id ? 'admin-tab--active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* Tab content */}
      <div className="admin-content">
        {activeTab === 'overview'  && <AdminStats stats={stats} />}
        {activeTab === 'bcr'       && <BCRPanel />}
        {activeTab === 'map'       && <ZoneMapPanel onZoneClick={handleMapZoneClick} />}
        {activeTab === 'fraud'     && <FraudQueuePanel />}
        {activeTab === 'drills'    && <DrillPanel onZoneSelect={(fn) => { drillZoneSelectRef.current = fn; }} />}
        {activeTab === 'verify'    && <VerificationPanel />}
        {activeTab === 'stress'    && <StressProofPanel />}
        {activeTab === 'reassign'  && <ReassignmentQueuePanel />}
        {activeTab === 'trigger-proof' && <TriggerProofPanel />}
        {activeTab === 'riqi'      && <RiqiProvenancePanel />}
        {activeTab === 'notif-preview' && <NotificationPreviewPanel />}
        {activeTab === 'ml'        && <MLStatusPanel />}
        {activeTab === 'checklist' && <DemoChecklist />}
        {activeTab === 'triggers'  && (
          <>
            <TriggerPanel />
            <ExclusionsCard />
          </>
        )}
      </div>
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
