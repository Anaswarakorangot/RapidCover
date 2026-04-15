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
import DrillPanel    from '../components/admin/DrillPanel';
import VerificationPanel from '../components/admin/VerificationPanel';
import StressProofPanel from '../components/admin/StressProofPanel';
import ReassignmentQueuePanel from '../components/admin/ReassignmentQueuePanel';
import TriggerProofPanel from '../components/admin/TriggerProofPanel';
import RiqiProvenancePanel from '../components/admin/RiqiProvenancePanel';
import NotificationPreviewPanel from '../components/admin/NotificationPreviewPanel';
import DemoChecklist from '../components/admin/DemoChecklist';
import SocialOraclePanel from '../components/admin/SocialOraclePanel';
import LiveDataPanel from '../components/admin/LiveDataPanel';
import InsurerIntelligencePanel from '../components/admin/InsurerIntelligencePanel';
import PaymentReconciliationPanel from '../components/admin/PaymentReconciliationPanel';
import AggregationPanel from '../components/admin/AggregationPanel';
import PartialDisruptionPanel from '../components/admin/PartialDisruptionPanel';
import PremiumCollectionPanel from '../components/admin/PremiumCollectionPanel';
import DemoModePanel from '../components/admin/DemoModePanel';
import './Admin.css';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export function Admin() {
  const [stats, setStats]           = useState(null);
  const [loading, setLoading]       = useState(true);
  const [statsError, setStatsError] = useState(false);
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
    setStatsError(false);
    try {
      const res = await fetch(`${API_BASE}/admin/panel/stats`);
      if (!res.ok) {
        throw new Error('Failed to load admin stats');
      }
      setStats(await res.json());
    } catch {
      setStats(null);
      setStatsError(true);
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
    { id: 'intelligence',    label: '\u{1F52E} Intelligence' },
    { id: 'map',             label: '\u{1F5FA} Zone Map' },
    { id: 'fraud',           label: '\u{1F50D} Fraud Queue' },
    { id: 'payments',        label: '\u{1F4B3} Payments' },
    { id: 'premium',         label: '\u{1F4B0} Premiums' },
    { id: 'demo',            label: '\u{1F3AD} Demo Mode' },
    { id: 'aggregation',     label: '\u{1F517} Aggregation' },
    { id: 'disruption',      label: '\u{1F4CA} Disruption' },
    { id: 'drills',          label: '\u{1F3AF} Drills' },
    { id: 'live-data',       label: '\u{1F4E1} Live API Data' },
    { id: 'verify',          label: '\u{1F50D} Verification' },
    { id: 'stress',          label: '\u26A1 Stress Proof' },
    { id: 'reassign',        label: '\u{1F504} Reassignments' },
    { id: 'trigger-proof',   label: '\u{1F3AF} Trigger Proof' },
    { id: 'riqi',            label: '\u{1F4CA} RIQI Provenance' },
    { id: 'notif-preview',   label: '\u{1F514} Notifications' },
    { id: 'checklist',       label: '\u2705 Demo Checklist' },
    { id: 'oracle',          label: '\u{1F52E} Auto-Oracle' },
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
        {activeTab === 'overview'  && (
          stats
            ? <AdminStats stats={stats} />
            : (
              <section className="admin-section">
                <div
                  style={{
                    background: 'var(--white)',
                    border: '1.5px solid var(--border)',
                    borderRadius: '24px',
                    padding: '2rem',
                    textAlign: 'center',
                  }}
                >
                  <h2 style={{ fontFamily: 'Nunito', fontWeight: 900, color: 'var(--text-dark)', marginBottom: '0.5rem' }}>
                    No admin stats available
                  </h2>
                  <p style={{ color: 'var(--text-light)', margin: 0 }}>
                    {statsError ? 'The panel stats endpoint is unavailable right now.' : 'No panel data has been recorded yet.'}
                  </p>
                </div>
              </section>
            )
        )}
        {activeTab === 'bcr'       && <BCRPanel />}
        {activeTab === 'intelligence' && <InsurerIntelligencePanel />}
        {activeTab === 'map'       && <ZoneMapPanel onZoneClick={handleMapZoneClick} />}
        {activeTab === 'fraud'     && <FraudQueuePanel />}
        {activeTab === 'payments'  && <PaymentReconciliationPanel />}
        {activeTab === 'premium'   && <PremiumCollectionPanel />}
        {activeTab === 'demo'      && <DemoModePanel />}
        {activeTab === 'aggregation' && <AggregationPanel />}
        {activeTab === 'disruption' && <PartialDisruptionPanel />}
        {activeTab === 'drills'    && <DrillPanel onZoneSelect={(fn) => { drillZoneSelectRef.current = fn; }} />}
        {activeTab === 'live-data' && <LiveDataPanel />}
        {activeTab === 'verify'    && <VerificationPanel />}
        {activeTab === 'stress'    && <StressProofPanel />}
        {activeTab === 'reassign'  && <ReassignmentQueuePanel />}
        {activeTab === 'trigger-proof' && <TriggerProofPanel />}
        {activeTab === 'riqi'      && <RiqiProvenancePanel />}
        {activeTab === 'notif-preview' && <NotificationPreviewPanel />}
        {activeTab === 'checklist' && <DemoChecklist />}
        {activeTab === 'oracle'    && <SocialOraclePanel />}
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
