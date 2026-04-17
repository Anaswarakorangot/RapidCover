// frontend/src/components/admin/TriggerProofPanel.jsx
// Platform Activity Simulation — admin toggle + eligibility + oracle proof

import { useState, useEffect } from 'react';
import { AdminLoader, AdminError, AdminEmpty, ProofCard } from './AdminProofShared';
import { authenticatedFetch } from '../../services/adminApi';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const PLATFORM_ICONS = { zepto: '⚡', blinkit: '🟡' };
const PLATFORM_OPTIONS = ['zepto', 'blinkit'];

export default function TriggerProofPanel() {
  const [proofData, setProofData] = useState(null);
  const [eligData, setEligData] = useState(null);
  const [oracleData, setOracleData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('platform');

  // Per-partner activity control
  const [partnerId, setPartnerId] = useState('');
  const [activityForm, setActivityForm] = useState(null);
  const [actLoading, setActLoading] = useState(false);
  const [activityMsg, setActivityMsg] = useState(null);

  useEffect(() => { loadAll(); }, []);

  async function loadAll() {
    setLoading(true); setError(null);
    try {
      const [platform, oracle] = await Promise.all([
        authenticatedFetch(`${API}/admin/panel/proof/platform-activity`).then(r => r.json()),
        authenticatedFetch(`${API}/admin/panel/proof/oracle-reliability`).then(r => r.json()),
      ]);
      setProofData(platform);
      setOracleData(oracle);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  async function loadPartnerActivity() {
    if (!partnerId) return;
    setActLoading(true); setActivityMsg(null);
    try {
      const res = await authenticatedFetch(`${API}/zones/partners/${partnerId}/activity`);
      if (!res.ok) throw new Error(`Partner ${partnerId} not found`);
      setActivityForm(await res.json());
      const eligRes = await authenticatedFetch(`${API}/zones/partners/${partnerId}/activity/eligibility`);
      if (eligRes.ok) setEligData(await eligRes.json());
    } catch (e) { setActivityMsg({ type: 'error', text: e.message }); }
    finally { setActLoading(false); }
  }

  async function saveActivity() {
    if (!activityForm || !partnerId) return;
    setActLoading(true); setActivityMsg(null);
    try {
      const res = await authenticatedFetch(`${API}/zones/partners/${partnerId}/activity`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform_logged_in: activityForm.platform_logged_in,
          active_shift: activityForm.active_shift,
          orders_accepted_recent: activityForm.orders_accepted_recent,
          orders_completed_recent: activityForm.orders_completed_recent,
          zone_dwell_minutes: activityForm.zone_dwell_minutes,
          suspicious_inactivity: activityForm.suspicious_inactivity,
          platform: activityForm.platform,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setActivityForm(await res.json());
      const eligRes = await authenticatedFetch(`${API}/zones/partners/${partnerId}/activity/eligibility`);
      if (eligRes.ok) setEligData(await eligRes.json());
      setActivityMsg({ type: 'success', text: 'Activity updated — claim eligibility re-evaluated.' });
    } catch (e) { setActivityMsg({ type: 'error', text: e.message }); }
    finally { setActLoading(false); }
  }

  const TABS = [
    { id: 'platform', label: '📱 Platform Activity' },
    { id: 'control', label: '🎛️ Admin Control' },
    { id: 'oracle', label: '🔮 Oracle Proof' },
    { id: 'trigger', label: '🎯 Trigger Eligibility' },
  ];

  if (loading) return <AdminLoader message="Loading proof data…" />;
  if (error) return <AdminError message={error} onRetry={loadAll} />;

  return (
    <section>
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)' }}>
          🎯 Trigger & Platform Proof
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-light)', marginTop: '0.3rem' }}>
          Platform activity simulation for Zepto & Blinkit partners, admin controls, oracle reliability, and trigger eligibility.
        </p>
      </div>

      {/* Sub-tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            style={{ padding: '0.5rem 1rem', borderRadius: '20px', border: '1.5px solid var(--border)', fontWeight: 700, fontSize: '0.82rem', cursor: 'pointer', background: activeTab === t.id ? 'var(--primary)' : 'var(--white)', color: activeTab === t.id ? 'white' : 'var(--text-mid)' }}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'platform' && <PlatformProofTab data={proofData} />}
      {activeTab === 'control' && (
        <AdminControlTab
          partnerId={partnerId}
          setPartnerId={setPartnerId}
          activityForm={activityForm}
          setActivityForm={setActivityForm}
          eligData={eligData}
          loading={actLoading}
          message={activityMsg}
          onLoad={loadPartnerActivity}
          onSave={saveActivity}
        />
      )}
      {activeTab === 'oracle' && <OracleProofTab data={oracleData} />}
      {activeTab === 'trigger' && <TriggerEligTab />}
    </section>
  );
}

// ── Platform proof tab ────────────────────────────────────────────────────────

function PlatformProofTab({ data }) {
  if (!data) return <AdminEmpty icon="📱" message="No platform activity data." />;

  const { total_sampled, platform_eligible, platform_ineligible, partners, admin_controls, notes } = data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Stats */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        {[
          { label: 'Sampled', value: total_sampled, color: 'var(--primary)' },
          { label: 'Eligible', value: platform_eligible, color: 'var(--green-primary)' },
          { label: 'Ineligible', value: platform_ineligible, color: 'var(--error)' },
        ].map(m => (
          <div key={m.label} style={{ flex: 1, minWidth: 100, padding: '0.875rem', borderRadius: '14px', background: 'var(--white)', border: `2px solid ${m.color}25`, textAlign: 'center' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: 900, color: m.color, fontFamily: 'Nunito' }}>{m.value ?? 0}</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-light)', fontWeight: 700, textTransform: 'uppercase' }}>{m.label}</div>
          </div>
        ))}
      </div>

      {/* Partner table */}
      <div>
        <p style={{ fontWeight: 800, fontSize: '0.78rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Partner Activity Sample</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {(partners || []).map(p => <PartnerRow key={p.partner_id} partner={p} />)}
        </div>
      </div>

      {/* Admin API endpoints */}
      {admin_controls && (
        <div style={{ padding: '1rem', background: 'var(--gray-bg)', borderRadius: '12px' }}>
          <p style={{ fontWeight: 800, fontSize: '0.78rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Admin API Endpoints</p>
          {Object.entries(admin_controls).map(([key, val]) => (
            <div key={key} style={{ display: 'flex', gap: '0.75rem', padding: '0.3rem 0', fontSize: '0.78rem' }}>
              <code style={{ color: 'var(--primary)', fontWeight: 700, minWidth: 180 }}>{key.replace(/_/g, ' ')}</code>
              <code style={{ color: 'var(--text-mid)' }}>{val}</code>
            </div>
          ))}
        </div>
      )}

      {/* Notes */}
      {notes?.length > 0 && (
        <div>
          <p style={{ fontWeight: 800, fontSize: '0.78rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>How It Works</p>
          <ul style={{ paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            {notes.map((n, i) => <li key={i} style={{ fontSize: '0.83rem', color: 'var(--text-mid)' }}>{n}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function PartnerRow({ partner }) {
  const active = partner.platform_logged_in && partner.active_shift;
  const score = Math.round((partner.platform_score || 0) * 100);
  const scoreColor = score >= 80 ? 'var(--green-primary)' : score >= 50 ? '#f59e0b' : 'var(--error)';
  const platformLabel = partner.platform || 'unknown';
  const icon = PLATFORM_ICONS[platformLabel] || '📱';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', background: 'var(--white)', borderRadius: '12px', border: '1.5px solid var(--border)', borderLeft: `4px solid ${active ? 'var(--green-primary)' : 'var(--error)'}` }}>
      <span style={{ fontSize: '1.1rem' }}>{icon}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dark)' }}>{partner.partner_name}</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span style={{ fontWeight: 700, textTransform: 'uppercase', background: '#f1f5f9', borderRadius: '4px', padding: '1px 5px', fontSize: '0.7rem' }}>{platformLabel}</span>
          <span>· {partner.orders_completed_recent} orders completed</span>
        </div>
      </div>
      <span style={{ fontSize: '0.72rem', fontWeight: 700, padding: '2px 8px', borderRadius: '8px', background: active ? '#dcfce7' : '#fef2f2', color: active ? '#166534' : '#991b1b' }}>
        {active ? '● ACTIVE' : '○ OFFLINE'}
      </span>
      <span style={{ fontSize: '0.82rem', fontWeight: 900, color: scoreColor }}>{score}%</span>
    </div>
  );
}

// ── Admin control tab ─────────────────────────────────────────────────────────

function AdminControlTab({ partnerId, setPartnerId, activityForm, setActivityForm, eligData, loading, message, onLoad, onSave }) {
  function toggle(field) {
    setActivityForm(f => ({ ...f, [field]: !f[field] }));
  }
  function setNum(field, val) {
    setActivityForm(f => ({ ...f, [field]: parseInt(val) || 0 }));
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ padding: '1rem', background: 'var(--white)', borderRadius: '14px', border: '1.5px solid var(--border)' }}>
        <p style={{ fontWeight: 800, fontSize: '0.82rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
          Load Partner Activity
        </p>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <input
            type="number" placeholder="Partner ID…"
            value={partnerId} onChange={e => setPartnerId(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && onLoad()}
            style={{ flex: 1, padding: '0.6rem 0.9rem', borderRadius: '10px', border: '1.5px solid var(--border)', fontSize: '0.9rem' }}
          />
          <button onClick={onLoad} disabled={!partnerId || loading}
            style={{ padding: '0.6rem 1.25rem', borderRadius: '10px', background: (!partnerId || loading) ? 'var(--text-light)' : 'var(--primary)', color: 'white', border: 'none', fontWeight: 800, fontSize: '0.85rem', cursor: (!partnerId || loading) ? 'not-allowed' : 'pointer' }}>
            {loading ? 'Loading…' : 'Load'}
          </button>
        </div>
      </div>

      {message && (
        <div style={{ padding: '0.75rem 1rem', borderRadius: '10px', background: message.type === 'success' ? '#dcfce7' : '#fef2f2', color: message.type === 'success' ? '#166534' : '#991b1b', fontSize: '0.85rem', fontWeight: 600 }}>
          {message.type === 'success' ? '✅' : '⚠️'} {message.text}
        </div>
      )}

      {activityForm && (
        <>
          <div style={{ padding: '1rem', background: 'var(--white)', borderRadius: '14px', border: '1.5px solid var(--border)' }}>
            <p style={{ fontWeight: 800, fontSize: '0.82rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '1rem' }}>
              Toggle Activity — Partner #{partnerId}
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {[
                { field: 'platform_logged_in', label: 'Platform Logged In' },
                { field: 'active_shift', label: 'Active Shift' },
                { field: 'suspicious_inactivity', label: 'Suspicious Inactivity Flag' },
              ].map(({ field, label }) => (
                <div key={field} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-dark)' }}>{label}</span>
                  <button onClick={() => toggle(field)}
                    style={{ padding: '0.4rem 1rem', borderRadius: '20px', fontWeight: 800, fontSize: '0.8rem', cursor: 'pointer', border: 'none', background: activityForm[field] ? 'var(--green-primary)' : '#ef4444', color: 'white' }}>
                    {activityForm[field] ? 'ON' : 'OFF'}
                  </button>
                </div>
              ))}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-dark)' }}>Orders Completed (Recent)</span>
                <input type="number" min={0} max={50} value={activityForm.orders_completed_recent}
                  onChange={e => setNum('orders_completed_recent', e.target.value)}
                  style={{ width: 70, padding: '0.35rem 0.5rem', borderRadius: '8px', border: '1.5px solid var(--border)', textAlign: 'center', fontWeight: 700, fontSize: '0.9rem' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-dark)' }}>Platform</span>
                <select value={activityForm.platform} onChange={e => setActivityForm(f => ({ ...f, platform: e.target.value }))}
                  style={{ padding: '0.35rem 0.6rem', borderRadius: '8px', border: '1.5px solid var(--border)', fontWeight: 700, fontSize: '0.85rem' }}>
                  {PLATFORM_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
            </div>

            <button onClick={onSave} disabled={loading}
              style={{ marginTop: '1.25rem', width: '100%', padding: '0.75rem', borderRadius: '12px', background: loading ? 'var(--text-light)' : 'var(--green-primary)', color: 'white', border: 'none', fontWeight: 800, fontSize: '0.9rem', cursor: loading ? 'wait' : 'pointer' }}>
              {loading ? 'Saving…' : '💾 Save & Re-evaluate Eligibility'}
            </button>
          </div>

          {/* Eligibility result */}
          {eligData && <EligibilityResult data={eligData} />}
        </>
      )}
    </div>
  );
}

function EligibilityResult({ data }) {
  const { eligible, score, reasons } = data;
  const scorePct = Math.round((score || 0) * 100);

  return (
    <div style={{ padding: '1rem', background: 'var(--white)', borderRadius: '14px', border: `2px solid ${eligible ? 'var(--green-primary)' : 'var(--error)'}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <span style={{ fontWeight: 900, fontSize: '0.9rem', fontFamily: 'Nunito', color: eligible ? 'var(--green-dark)' : '#991b1b' }}>
          {eligible ? '✅ Claim Eligible' : '❌ Claim Blocked'}
        </span>
        <span style={{ fontWeight: 900, fontSize: '1rem', color: scorePct >= 80 ? 'var(--green-primary)' : '#f59e0b' }}>
          Score: {scorePct}%
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        {(reasons || []).map((r, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.8rem' }}>
            <span style={{ color: r.pass ? 'var(--green-primary)' : 'var(--error)', fontWeight: 800, flexShrink: 0 }}>{r.pass ? '✓' : '✕'}</span>
            <span style={{ color: 'var(--text-dark)', fontWeight: 700, minWidth: 160 }}>{r.check?.replace(/_/g, ' ')}</span>
            <span style={{ color: 'var(--text-light)' }}>{r.note}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Oracle proof tab ──────────────────────────────────────────────────────────

function OracleProofTab({ data }) {
  if (!data) return <AdminEmpty icon="🔮" message="No oracle data." />;

  const { sample_trigger_confidence, notes } = data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <p style={{ fontWeight: 800, fontSize: '0.78rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Source Reliability</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {Object.entries(data.sources || {}).map(([name, info]) => (
            <OracleSourceRow key={name} name={name} info={info} />
          ))}
        </div>
      </div>

      {sample_trigger_confidence && (
        <div style={{ padding: '1rem', background: 'var(--white)', borderRadius: '14px', border: '1.5px solid var(--border)' }}>
          <p style={{ fontWeight: 800, fontSize: '0.78rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Sample Trigger Decision</p>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-mid)', marginBottom: '0.5rem' }}>{sample_trigger_confidence.reason}</div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <div style={{ fontSize: '0.8rem' }}>
              <span style={{ color: 'var(--text-light)' }}>Decision: </span>
              <span style={{ fontWeight: 800, color: 'var(--text-dark)' }}>{sample_trigger_confidence.decision?.replace(/_/g, ' ')}</span>
            </div>
            <div style={{ fontSize: '0.8rem' }}>
              <span style={{ color: 'var(--text-light)' }}>Confidence: </span>
              <span style={{ fontWeight: 800, color: 'var(--green-primary)' }}>
                {Math.round((sample_trigger_confidence.trigger_confidence_score || 0) * 100)}%
              </span>
            </div>
          </div>
        </div>
      )}

      {notes?.length > 0 && (
        <div>
          <p style={{ fontWeight: 800, fontSize: '0.78rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>How Oracle Works</p>
          <ul style={{ paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            {notes.map((n, i) => <li key={i} style={{ fontSize: '0.83rem', color: 'var(--text-mid)' }}>{n}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function OracleSourceRow({ name, info }) {
  const badge = info.badge || 'unknown';
  const COLORS = { live: '#22c55e', mock: '#f59e0b', stale: '#ef4444', unknown: '#94a3b8' };
  const color = COLORS[badge] || COLORS.unknown;
  const score = Math.round((info.reliability_score || 0) * 100);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.65rem 0.875rem', background: 'var(--white)', borderRadius: '10px', border: '1.5px solid var(--border)' }}>
      <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
      <span style={{ flex: 1, fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-dark)' }}>{name}</span>
      <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '2px 8px', borderRadius: '8px', background: `${color}20`, color }}>{badge.toUpperCase()}</span>
      <span style={{ fontWeight: 800, fontSize: '0.82rem', color: score >= 80 ? 'var(--green-primary)' : '#f59e0b' }}>{score}%</span>
    </div>
  );
}

// ── Trigger eligibility tab (existing proof) ──────────────────────────────────

function TriggerEligTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true); setError(null);
    try {
      const res = await authenticatedFetch(`${API}/admin/panel/proof/trigger-eligibility`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <AdminLoader message="Checking trigger eligibility…" />;
  if (error) return <AdminError message={error} onRetry={load} />;
  if (!data) return <AdminEmpty icon="🎯" message="No eligibility data" />;

  const { input, output, notes } = data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
        {[
          { label: 'Partners Checked', value: input?.partners_checked },
          { label: 'Zones Checked', value: input?.zones_checked },
          { label: 'With Pin Code', value: output?.partners_with_pin_code, good: true },
          { label: 'Without Pin Code', value: output?.partners_without_pin_code, bad: true },
          { label: 'Zones with Coverage', value: output?.zones_with_coverage_data, good: true },
          { label: 'Zones without Coverage', value: output?.zones_without_coverage_data, bad: true },
        ].map(m => (
          <div key={m.label} style={{ padding: '0.875rem', borderRadius: '12px', background: 'var(--white)', border: '1.5px solid var(--border)', textAlign: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 900, fontFamily: 'Nunito', color: m.good ? 'var(--green-primary)' : m.bad ? 'var(--error)' : 'var(--primary)' }}>{m.value ?? 0}</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-light)', fontWeight: 700, textTransform: 'uppercase', marginTop: '0.15rem' }}>{m.label}</div>
          </div>
        ))}
      </div>
      {notes?.length > 0 && (
        <ul style={{ paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {notes.map((n, i) => <li key={i} style={{ fontSize: '0.83rem', color: 'var(--text-mid)' }}>{n}</li>)}
        </ul>
      )}
    </div>
  );
}