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
import FraudQueuePanel    from '../components/admin/FraudQueuePanel';
import { SettingsPanel }     from '../components/admin/SettingsPanel';
import DrillPanel           from '../components/admin/DrillPanel';
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
import DemoModeScenarioPanel from '../components/admin/DemoModeScenarioPanel';
import './Admin.css';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export function Admin() {
  const [stats, setStats]           = useState(null);
  const [loading, setLoading]       = useState(true);
  const [statsError, setStatsError] = useState(false);
  const [activeTab, setActiveTab]   = useState('overview');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const drillZoneSelectRef = useRef(null);

  useEffect(() => {
    loadStats();
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

  const today = new Date().toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' });


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
    { id: 'settings',        label: '\u2699\u{FE0F} Settings' },
    { id: 'triggers',        label: '\u{2699}\u{FE0F} Legacy Sim' },
  ];

  // Handle zone selection from map to drill panel
  function handleMapZoneClick(zoneCode) {
    if (drillZoneSelectRef.current) {
      drillZoneSelectRef.current(zoneCode);
      setActiveTab('drills');
    }
  }

  const MENU_GROUPS = [
    {
      label: 'Dashboards',
      items: ['overview', 'intelligence', 'map', 'bcr', 'live-data']
    },
    {
      label: 'Operations',
      items: ['fraud', 'payments', 'premium', 'aggregation', 'disruption', 'reassign']
    },
    {
      label: 'Tools & Testing',
      items: ['drills', 'verify', 'stress', 'trigger-proof', 'riqi', 'notif-preview', 'checklist', 'oracle', 'triggers']
    }
  ];

  if (loading) {
    return (
      <div className="admin-loader">
        <div className="admin-loader__spinner" />
        <span>Loading control panel...</span>
      </div>
    );
  }

  return (
    <div className={`admin-layout ${isSidebarOpen ? 'sidebar-open' : ''}`}>
      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div 
          className="sidebar-overlay" 
          onClick={() => setIsSidebarOpen(false)} 
        />
      )}

      {/* Sidebar Navigation */}
      <aside className={`admin-sidebar ${isSidebarOpen ? 'admin-sidebar--open' : ''}`}>
        <div className="sidebar-logo">
          <span style={{ fontSize: '1.2rem' }}>🛡️</span>
          RapidCover
        </div>
        <div className="sidebar-menu">
          {MENU_GROUPS.map(group => (
            <div key={group.label} className="menu-section">
              <span className="menu-label">{group.label}</span>
              {group.items.map(tabId => {
                const tab = TABS.find(t => t.id === tabId);
                if (!tab) return null;
                return (
                  <button
                    key={tabId}
                    className={`menu-item ${activeTab === tabId ? 'menu-item--active' : ''}`}
                    onClick={() => setActiveTab(tabId)}
                  >
                    <span className="menu-item__icon">{tab.label.split(' ')[0]}</span>
                    {tab.label.split(' ').slice(1).join(' ') || tab.label}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </aside>

      <main className="admin-main">
        {/* Top Navigation Bar */}
        <header className="admin-topnav">
          <div className="topnav-left">
            <button 
              className="burger-menu" 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            >
              ☰
            </button>
            <input type="text" className="topnav-search" placeholder="Search for stats, workers, or claims..." />
            <button 
              className={`demo-top-toggle ${activeTab === 'demo' ? 'demo-top-toggle--active' : ''}`}
              onClick={() => setActiveTab('demo')}
              style={{ 
                width: 'auto', 
                padding: '0.4rem 1.25rem', 
                borderRadius: '30px', 
                fontSize: '0.75rem', 
                fontWeight: 800,
                letterSpacing: '0.05em',
                marginLeft: '1rem', 
                cursor: 'pointer',
                transition: 'all 0.2s',
                border: activeTab === 'demo' ? 'none' : '1px solid var(--border-light)',
                background: activeTab === 'demo' ? 'var(--primary)' : 'var(--white)',
                color: activeTab === 'demo' ? 'var(--white)' : 'var(--text-dark)',
                textTransform: 'uppercase'
              }}
            >
              Demo Mode
            </button>
          </div>
          
          <div className="topnav-right">
            <div className="topnav-icon">🔔 <span style={{ position: 'absolute', top: -4, right: -4, background: 'var(--danger)', color: 'white', fontSize: '0.6rem', padding: '1px 4px', borderRadius: '10px' }}>3</span></div>
            <div 
              className={`topnav-icon ${activeTab === 'settings' ? 'topnav-icon--active' : ''}`}
              onClick={() => setActiveTab('settings')}
            >
              ⚙️
            </div>
            
            <div className="topnav-profile">
              <div className="profile-info" style={{ textAlign: 'right' }}>
                <div className="profile-name">Admin User</div>
                <div className="profile-role">Platform Manager</div>
              </div>
              <div className="profile-avatar">AD</div>
            </div>
          </div>
        </header>

        {/* Dynamic Content Area */}
        <div className="admin-content-scroll">
          <div style={{ marginBottom: '2rem' }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-dark)', margin: 0 }}>
              {TABS.find(t => t.id === activeTab)?.label.split(' ').slice(1).join(' ') || "Dashboard"}
            </h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              RapidCover Insurance · {activeTab.toUpperCase()} · {today}
            </p>
          </div>

          <div className="admin-content">
            {activeTab === 'overview'  && (
              stats
                ? <AdminStats stats={stats} />
                : (
                  <section className="admin-section">
                    <div style={{ background: 'var(--white)', border: '1px solid var(--border-light)', borderRadius: '12px', padding: '2rem', textAlign: 'center' }}>
                      <h2 style={{ fontWeight: 800, color: 'var(--text-dark)', marginBottom: '0.5rem' }}>No admin stats available</h2>
                      <p style={{ color: 'var(--text-muted)', margin: 0 }}>{statsError ? 'Backend unavailable' : 'No data recorded'}</p>
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
            {activeTab === 'demo'      && <DemoModeScenarioPanel />}
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
            {activeTab === 'settings'  && <SettingsPanel />}
            {activeTab === 'triggers'  && (
              <>
                <TriggerPanel />
                <ExclusionsCard />
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
