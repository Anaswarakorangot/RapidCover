import { useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const EMPTY_FORM = {
  scenario_type: 'standard_trigger',
  zone_id: '',
  trigger_type: 'rain',
  severity: 4,
  enforce_restrictions: true,
  inject_sustained_days: 0,
  partial_factor_override: '',
  expected_orders: '',
  actual_orders: '',
  auto_mark_paid: true,
  disruption_hours: '',
};

function StatPill({ label, value, tone = 'default' }) {
  const tones = {
    default: { background: '#f3f4f6', color: '#111827' },
    green: { background: '#dcfce7', color: '#166534' },
    amber: { background: '#fef3c7', color: '#92400e' },
    red: { background: '#fee2e2', color: '#991b1b' },
  };

  return (
    <span style={{ ...tones[tone], borderRadius: '999px', padding: '0.45rem 0.8rem', fontSize: '0.82rem', fontWeight: 800 }}>
      {label}: {value}
    </span>
  );
}

function toPayload(form) {
  return {
    scenario_type: form.scenario_type,
    zone_id: Number(form.zone_id),
    trigger_type: form.trigger_type,
    severity: Number(form.severity),
    enforce_restrictions: form.enforce_restrictions,
    inject_sustained_days: Number(form.inject_sustained_days || 0),
    partial_factor_override: form.partial_factor_override === '' ? null : Number(form.partial_factor_override),
    expected_orders: form.expected_orders === '' ? null : Number(form.expected_orders),
    actual_orders: form.actual_orders === '' ? null : Number(form.actual_orders),
    auto_mark_paid: form.auto_mark_paid,
    disruption_hours: form.disruption_hours === '' ? null : Number(form.disruption_hours),
  };
}

export default function DemoModeScenarioPanel() {
  const [demoStatus, setDemoStatus] = useState(null);
  const [zones, setZones] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [recentRuns, setRecentRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [cleaningRunId, setCleaningRunId] = useState(null);

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [statusRes, scenariosRes] = await Promise.all([
        fetch(`${API}/admin/panel/demo-mode/status`),
        fetch(`${API}/admin/panel/demo-mode/scenarios`),
      ]);
      const statusData = await statusRes.json();
      const scenarioData = await scenariosRes.json();
      setDemoStatus(statusData);
      setZones(scenarioData.zones || []);
      setScenarios(scenarioData.scenarios || []);
      setRecentRuns(scenarioData.recent_runs || statusData.recent_runs || []);
      if (!form.zone_id && scenarioData.zones?.length) {
        setForm((current) => ({ ...current, zone_id: String(scenarioData.zones[0].id) }));
      }
    } catch (error) {
      console.error('Failed to load demo mode data', error);
      alert('Failed to load demo mode data');
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle() {
    if (!demoStatus) return;
    setToggling(true);
    try {
      const res = await fetch(`${API}/admin/panel/demo-mode/toggle?enabled=${!demoStatus.enabled}`, { method: 'POST' });
      const data = await res.json();
      setDemoStatus(data);
    } catch (error) {
      console.error('Failed to toggle demo mode', error);
      alert('Failed to toggle demo mode');
    } finally {
      setToggling(false);
    }
  }

  function applyScenarioDefaults(scenarioId) {
    const scenario = scenarios.find((item) => item.id === scenarioId);
    if (!scenario) return;
    const defaults = scenario.defaults || {};
    setForm((current) => ({
      ...current,
      scenario_type: scenarioId,
      trigger_type: defaults.trigger_type || 'rain',
      severity: defaults.severity ?? 4,
      inject_sustained_days: defaults.inject_sustained_days ?? 0,
      partial_factor_override: defaults.partial_factor_override ?? '',
      expected_orders: defaults.expected_orders ?? '',
      actual_orders: defaults.actual_orders ?? '',
      auto_mark_paid: defaults.auto_mark_paid ?? true,
    }));
  }

  async function handleRun(event) {
    event.preventDefault();
    if (!form.zone_id) {
      alert('Select a zone first');
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`${API}/admin/panel/demo-mode/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(toPayload(form)),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to run scenario');
      setSelectedRun(data);
      await loadAll();
    } catch (error) {
      console.error('Failed to run demo scenario', error);
      alert(error.message || 'Failed to run demo scenario');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSelectRun(runId) {
    try {
      const res = await fetch(`${API}/admin/panel/demo-mode/run/${runId}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to load run');
      setSelectedRun(data);
    } catch (error) {
      console.error('Failed to load run', error);
      alert(error.message || 'Failed to load run');
    }
  }

  async function handleCleanup(runId) {
    setCleaningRunId(runId);
    try {
      const res = await fetch(`${API}/admin/panel/demo-mode/run/${runId}/cleanup`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to clean up run');
      setSelectedRun(data);
      await loadAll();
    } catch (error) {
      console.error('Failed to clean up run', error);
      alert(error.message || 'Failed to clean up run');
    } finally {
      setCleaningRunId(null);
    }
  }

  if (loading || !demoStatus) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-mid)' }}>Loading demo controls...</div>;
  }

  const isEnabled = demoStatus.enabled;
  const scenario = scenarios.find((item) => item.id === form.scenario_type);
  const claimSummary = selectedRun?.claims?.summary || null;

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', display: 'grid', gap: '1.5rem' }}>
      <div style={{ background: isEnabled ? '#fef3c7' : 'white', border: `2px solid ${isEnabled ? '#f59e0b' : 'var(--border)'}`, borderRadius: '20px', padding: '1.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'start' }}>
          <div>
            <h2 style={{ margin: 0, marginBottom: '0.5rem', fontFamily: 'Nunito', fontWeight: 900, color: isEnabled ? '#92400e' : 'var(--text-dark)' }}>
              {isEnabled ? 'Demo Override Active' : 'Production Mode'}
            </h2>
            <p style={{ margin: 0, color: isEnabled ? '#78350f' : 'var(--text-mid)', lineHeight: 1.6 }}>{demoStatus.description}</p>
          </div>
          <button
            onClick={handleToggle}
            disabled={toggling}
            style={{ background: isEnabled ? '#ef4444' : 'var(--green-primary)', color: 'white', border: 'none', borderRadius: '12px', padding: '0.95rem 1.4rem', fontWeight: 800, cursor: toggling ? 'not-allowed' : 'pointer' }}
          >
            {toggling ? 'Switching...' : isEnabled ? 'Disable Demo Mode' : 'Enable Demo Mode'}
          </button>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', marginTop: '1rem' }}>
          <StatPill label="Adverse Selection" value={isEnabled ? 'Bypassed' : 'Enforced'} tone={isEnabled ? 'amber' : 'green'} />
          <StatPill label="Activity Gate" value={isEnabled ? 'Bypassed' : 'Enforced'} tone={isEnabled ? 'amber' : 'green'} />
          <StatPill label="Payout Mode" value="Mock Only" tone="green" />
        </div>
      </div>

      <div style={{ display: 'grid', gap: '1.5rem', gridTemplateColumns: selectedRun ? '1.1fr 0.9fr' : '1fr' }}>
        <form onSubmit={handleRun} style={{ background: 'white', border: '1.5px solid var(--border)', borderRadius: '20px', padding: '1.75rem', display: 'grid', gap: '1rem' }}>
          <div>
            <h3 style={{ margin: 0, marginBottom: '0.4rem', fontFamily: 'Nunito', fontWeight: 900 }}>Scenario Runner</h3>
            <p style={{ margin: 0, color: 'var(--text-mid)', fontSize: '0.92rem' }}>Runs hit the real trigger and claim pipeline for the selected live zone while keeping payouts mocked.</p>
          </div>

          <div>
            <label style={{ display: 'block', fontWeight: 800, marginBottom: '0.45rem' }}>Scenario</label>
            <select
              value={form.scenario_type}
              onChange={(e) => applyScenarioDefaults(e.target.value)}
              style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1.5px solid var(--border)' }}
            >
              {scenarios.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
            <p style={{ margin: '0.5rem 0 0', color: 'var(--text-mid)', fontSize: '0.84rem' }}>{scenario?.description}</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontWeight: 800, marginBottom: '0.45rem' }}>Zone</label>
              <select value={form.zone_id} onChange={(e) => setForm({ ...form, zone_id: e.target.value })} style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1.5px solid var(--border)' }}>
                {zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name} ({zone.code})</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 800, marginBottom: '0.45rem' }}>Trigger</label>
              <select value={form.trigger_type} onChange={(e) => setForm({ ...form, trigger_type: e.target.value })} style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1.5px solid var(--border)' }}>
                <option value="rain">Rain</option>
                <option value="heat">Heat</option>
                <option value="aqi">AQI</option>
                <option value="shutdown">Shutdown</option>
                <option value="closure">Closure</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 800, marginBottom: '0.45rem' }}>Severity</label>
              <input type="number" min="1" max="5" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1.5px solid var(--border)' }} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontWeight: 800, marginBottom: '0.45rem' }}>Sustained Days</label>
              <input type="number" min="0" max="5" value={form.inject_sustained_days} onChange={(e) => setForm({ ...form, inject_sustained_days: e.target.value })} style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1.5px solid var(--border)' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 800, marginBottom: '0.45rem' }}>Partial Factor</label>
              <input type="number" min="0" max="1" step="0.05" value={form.partial_factor_override} onChange={(e) => setForm({ ...form, partial_factor_override: e.target.value })} placeholder="0.5" style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1.5px solid var(--border)' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 800, marginBottom: '0.45rem' }}>Expected Orders</label>
              <input type="number" min="0" value={form.expected_orders} onChange={(e) => setForm({ ...form, expected_orders: e.target.value })} style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1.5px solid var(--border)' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 800, marginBottom: '0.45rem' }}>Actual Orders</label>
              <input type="number" min="0" value={form.actual_orders} onChange={(e) => setForm({ ...form, actual_orders: e.target.value })} style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1.5px solid var(--border)' }} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontWeight: 700 }}>
              <input type="checkbox" checked={form.enforce_restrictions} onChange={(e) => setForm({ ...form, enforce_restrictions: e.target.checked })} />
              Enforce production restrictions during run
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontWeight: 700 }}>
              <input type="checkbox" checked={form.auto_mark_paid} onChange={(e) => setForm({ ...form, auto_mark_paid: e.target.checked })} />
              Auto-mark approved claims as paid
            </label>
          </div>

          <button type="submit" disabled={submitting} style={{ background: 'var(--green-primary)', color: 'white', border: 'none', borderRadius: '12px', padding: '1rem', fontWeight: 800, cursor: submitting ? 'not-allowed' : 'pointer', opacity: submitting ? 0.65 : 1 }}>
            {submitting ? 'Running scenario...' : 'Run Scenario'}
          </button>
        </form>

        {selectedRun && (
          <div style={{ background: 'white', border: '1.5px solid var(--border)', borderRadius: '20px', padding: '1.75rem', display: 'grid', gap: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'start' }}>
              <div>
                <h3 style={{ margin: 0, marginBottom: '0.35rem', fontFamily: 'Nunito', fontWeight: 900 }}>Run #{selectedRun.run_id}</h3>
                <p style={{ margin: 0, color: 'var(--text-mid)', fontSize: '0.9rem' }}>{selectedRun.zone?.name} · {selectedRun.trigger?.type} · {selectedRun.status}</p>
              </div>
              <button
                onClick={() => handleCleanup(selectedRun.run_id)}
                disabled={cleaningRunId === selectedRun.run_id}
                style={{ background: '#111827', color: 'white', border: 'none', borderRadius: '12px', padding: '0.8rem 1rem', fontWeight: 800, cursor: cleaningRunId === selectedRun.run_id ? 'not-allowed' : 'pointer' }}
              >
                {cleaningRunId === selectedRun.run_id ? 'Cleaning...' : 'Cleanup Run'}
              </button>
            </div>

            {claimSummary && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem' }}>
                <StatPill label="Claims" value={claimSummary.total} />
                <StatPill label="Paid" value={claimSummary.paid} tone="green" />
                <StatPill label="Approved" value={claimSummary.approved} tone="amber" />
                <StatPill label="Rejected" value={claimSummary.rejected} tone="red" />
              </div>
            )}

            <div style={{ padding: '1rem', borderRadius: '14px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
              <div style={{ fontWeight: 800, marginBottom: '0.5rem' }}>Purchase Check Proof</div>
              <div style={{ fontSize: '0.88rem', color: 'var(--text-dark)', lineHeight: 1.7 }}>
                <div>Production before run: {String(selectedRun.purchase_checks?.before_run_production?.available)} · {selectedRun.purchase_checks?.before_run_production?.reason}</div>
                <div>Production after run: {String(selectedRun.purchase_checks?.after_run_production?.available)} · {selectedRun.purchase_checks?.after_run_production?.reason}</div>
                <div>Demo override after run: {String(selectedRun.purchase_checks?.after_run_demo_override?.available)} · {selectedRun.purchase_checks?.after_run_demo_override?.reason}</div>
              </div>
            </div>

            <div style={{ padding: '1rem', borderRadius: '14px', background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
              <div style={{ fontWeight: 800, marginBottom: '0.5rem', color: '#166534' }}>Visibility Checks</div>
              <div style={{ display: 'grid', gap: '0.4rem', color: '#166534', fontSize: '0.88rem' }}>
                <div>Partner zone alert: {selectedRun.visibility?.partner_zone_alert ? 'Yes' : 'No'}</div>
                <div>Partner claims history: {selectedRun.visibility?.partner_claims_history ? 'Yes' : 'No'}</div>
                <div>Latest payout banner: {selectedRun.visibility?.partner_latest_payout_banner ? 'Yes' : 'No'}</div>
                <div>Payout mode: {selectedRun.payout_mode?.mode}</div>
              </div>
            </div>

            <div>
              <div style={{ fontWeight: 800, marginBottom: '0.6rem' }}>Claim Samples</div>
              <div style={{ display: 'grid', gap: '0.7rem', maxHeight: '340px', overflow: 'auto' }}>
                {(selectedRun.claims?.items || []).map((claim) => (
                  <div key={claim.claim_id} style={{ border: '1px solid var(--border)', borderRadius: '14px', padding: '0.9rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', fontWeight: 800 }}>
                      <span>Claim #{claim.claim_id}</span>
                      <span style={{ textTransform: 'capitalize' }}>{claim.status}</span>
                    </div>
                    <div style={{ marginTop: '0.35rem', color: 'var(--text-mid)', fontSize: '0.84rem', lineHeight: 1.6 }}>
                      <div>Amount: ₹{claim.amount}</div>
                      <div>Partial factor: {claim.payout?.partial_factor ?? 'n/a'} · Sustained: {claim.payout?.is_sustained ? 'Yes' : 'No'}</div>
                      <div>Latest payout banner: {claim.partner_visibility?.latest_payout_banner ? 'Yes' : 'No'}</div>
                    </div>
                  </div>
                ))}
                {selectedRun.claims?.items?.length === 0 && <div style={{ color: 'var(--text-mid)' }}>No claims were created for this run.</div>}
              </div>
            </div>
          </div>
        )}
      </div>

      <div style={{ background: 'white', border: '1.5px solid var(--border)', borderRadius: '20px', padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ margin: 0, fontFamily: 'Nunito', fontWeight: 900 }}>Recent Runs</h3>
            <p style={{ margin: '0.25rem 0 0', color: 'var(--text-mid)', fontSize: '0.9rem' }}>Re-open any prior run summary or clean it up after the walkthrough.</p>
          </div>
          <button onClick={loadAll} style={{ background: '#eef2ff', color: '#3730a3', border: 'none', borderRadius: '12px', padding: '0.75rem 1rem', fontWeight: 800, cursor: 'pointer' }}>Refresh</button>
        </div>

        <div style={{ display: 'grid', gap: '0.8rem' }}>
          {recentRuns.map((run) => (
            <div key={run.run_id} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center', border: '1px solid var(--border)', borderRadius: '14px', padding: '0.9rem 1rem' }}>
              <div>
                <div style={{ fontWeight: 800 }}>#{run.run_id} · {run.scenario_type}</div>
                <div style={{ color: 'var(--text-mid)', fontSize: '0.84rem' }}>{run.zone?.name} · {run.trigger?.type} · {run.status}</div>
              </div>
              <div style={{ display: 'flex', gap: '0.6rem' }}>
                <button onClick={() => handleSelectRun(run.run_id)} style={{ background: '#f3f4f6', border: 'none', borderRadius: '10px', padding: '0.7rem 0.9rem', fontWeight: 700, cursor: 'pointer' }}>Open</button>
                <button onClick={() => handleCleanup(run.run_id)} disabled={cleaningRunId === run.run_id || run.status === 'cleaned_up'} style={{ background: '#111827', color: 'white', border: 'none', borderRadius: '10px', padding: '0.7rem 0.9rem', fontWeight: 700, cursor: cleaningRunId === run.run_id || run.status === 'cleaned_up' ? 'not-allowed' : 'pointer', opacity: run.status === 'cleaned_up' ? 0.5 : 1 }}>
                  {run.status === 'cleaned_up' ? 'Cleaned' : cleaningRunId === run.run_id ? 'Cleaning...' : 'Cleanup'}
                </button>
              </div>
            </div>
          ))}
          {recentRuns.length === 0 && <div style={{ color: 'var(--text-mid)' }}>No demo runs yet.</div>}
        </div>
      </div>
    </div>
  );
}
