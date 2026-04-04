// frontend/src/components/admin/LiveDataPanel.jsx
// Oracle Reliability Engine + Live API Data + Platform Activity Fleet View

import { useState, useEffect } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const BADGE_COLORS = {
  live: { bg: '#dcfce7', color: '#166534', dot: '#22c55e' },
  mock: { bg: '#fef9c3', color: '#92400e', dot: '#f59e0b' },
  stale: { bg: '#fef2f2', color: '#991b1b', dot: '#ef4444' },
  unknown: { bg: '#f3f4f6', color: '#6b7280', dot: '#9ca3af' },
  healthy: { bg: '#dcfce7', color: '#166534' },
  degraded: { bg: '#fef9c3', color: '#92400e' },
  stale_sys: { bg: '#fef2f2', color: '#991b1b' },
  mock_mode: { bg: '#f3f4f6', color: '#6b7280' },
};

const DECISION_COLORS = {
  fire: { bg: '#dcfce7', color: '#166534', icon: '🔥' },
  hold: { bg: '#fef2f2', color: '#991b1b', icon: '⏸️' },
  manual_review_simulated: { bg: '#fef9c3', color: '#92400e', icon: '👁️' },
  fallback_mock_mode: { bg: '#f3f4f6', color: '#6b7280', icon: '🎭' },
};

export default function LiveDataPanel() {
  const [liveData, setLiveData] = useState(null);
  const [oracle, setOracle] = useState(null);
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState('');
  const [zoneData, setZoneData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastFetch, setLastFetch] = useState(null);
  const [activeTab, setActiveTab] = useState('oracle');

  useEffect(() => {
    fetchZones();
    fetchLiveData();
    fetchOracle();
  }, []);

  useEffect(() => {
    if (selectedZone) fetchZoneData();
  }, [selectedZone]);

  async function fetchZones() {
    try {
      const res = await fetch(`${API}/zones`);
      if (res.ok) {
        const list = await res.json();
        setZones(list);
        if (list.length > 0) setSelectedZone(list[0].code);
      }
    } catch (err) { console.error('zones:', err); }
  }

  async function fetchLiveData() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/admin/panel/live-data`);
      if (res.ok) { setLiveData(await res.json()); setLastFetch(new Date()); }
    } catch (err) { console.error('live-data:', err); }
    setLoading(false);
  }

  async function fetchOracle() {
    try {
      const res = await fetch(`${API}/admin/panel/oracle-reliability`);
      if (res.ok) setOracle(await res.json());
    } catch (err) { console.error('oracle:', err); }
  }

  async function fetchZoneData() {
    if (!selectedZone) return;
    try {
      const res = await fetch(`${API}/admin/panel/live-data?zone_code=${selectedZone}`);
      if (res.ok) setZoneData(await res.json());
    } catch (err) { console.error('zone data:', err); }
  }

  const TABS = [
    { id: 'oracle', label: '🔮 Oracle Engine' },
    { id: 'sources', label: '📡 Data Sources' },
    { id: 'activity', label: '📱 Platform Activity' },
    { id: 'zone', label: '🌤️ Zone Data' },
  ];

  return (
    <section>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)' }}>
            📡 Live Data & Oracle Engine
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-light)', marginTop: '0.3rem' }}>
            Source reliability, trigger confidence decisions, platform activity, and live API readings.
          </p>
        </div>
        <button
          onClick={() => { fetchLiveData(); fetchOracle(); }}
          disabled={loading}
          style={{ padding: '0.65rem 1.25rem', borderRadius: '10px', background: loading ? 'var(--text-light)' : 'var(--primary)', color: 'white', border: 'none', fontWeight: 800, fontSize: '0.85rem', cursor: loading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
        >
          {loading ? <Spinner /> : '🔄'} Refresh
        </button>
      </div>

      {lastFetch && (
        <p style={{ fontSize: '0.75rem', color: 'var(--text-light)', marginBottom: '1rem' }}>
          Last fetched: {lastFetch.toLocaleTimeString()}
        </p>
      )}

      {/* System health banner */}
      {liveData?.oracle && <HealthBanner oracle={liveData.oracle} />}

      {/* Sub-tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            style={{ padding: '0.5rem 1rem', borderRadius: '20px', border: '1.5px solid var(--border)', fontWeight: 700, fontSize: '0.82rem', cursor: 'pointer', background: activeTab === t.id ? 'var(--primary)' : 'var(--white)', color: activeTab === t.id ? 'white' : 'var(--text-mid)' }}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'oracle' && <OracleTab oracle={oracle} liveData={liveData} />}
      {activeTab === 'sources' && <SourcesTab liveData={liveData} />}
      {activeTab === 'activity' && <ActivityTab liveData={liveData} />}
      {activeTab === 'zone' && <ZoneTab zones={zones} selectedZone={selectedZone} setSelectedZone={setSelectedZone} zoneData={zoneData} liveData={liveData} />}
    </section>
  );
}

// ── Health banner ─────────────────────────────────────────────────────────────

function HealthBanner({ oracle }) {
  const health = oracle.system_health || 'unknown';
  const key = health === 'stale' ? 'stale_sys' : health;
  const colors = BADGE_COLORS[key] || BADGE_COLORS.unknown;
  const icons = { healthy: '✅', degraded: '⚠️', stale: '🕑', mock_mode: '🎭' };

  return (
    <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', padding: '1rem 1.25rem', background: colors.bg, border: `1.5px solid ${colors.color}30`, borderRadius: '14px', alignItems: 'center', flexWrap: 'wrap' }}>
      <span style={{ fontSize: '1.5rem' }}>{icons[health] || '❓'}</span>
      <div>
        <div style={{ fontWeight: 900, fontSize: '1rem', color: colors.color, fontFamily: 'Nunito', textTransform: 'uppercase' }}>
          {health.replace('_', ' ')}
        </div>
        <div style={{ fontSize: '0.8rem', color: colors.color, opacity: 0.8 }}>
          {oracle.live_sources} live · {oracle.mock_sources} mock · {oracle.stale_sources} stale · avg reliability {Math.round((oracle.average_reliability || 0) * 100)}%
        </div>
      </div>
    </div>
  );
}

// ── Oracle tab ────────────────────────────────────────────────────────────────

function OracleTab({ oracle, liveData }) {
  if (!oracle) return <p style={{ color: 'var(--text-light)', fontSize: '0.9rem' }}>Loading oracle data…</p>;

  const examples = oracle.example_trigger_decisions || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Per-source reliability */}
      <div>
        <p style={{ fontWeight: 800, fontSize: '0.8rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Source Reliability Scores</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {Object.entries(oracle.sources || {}).map(([name, info]) => (
            <SourceReliabilityRow key={name} name={name} info={info} />
          ))}
        </div>
      </div>

      {/* Example trigger decisions */}
      {Object.keys(examples).length > 0 && (
        <div>
          <p style={{ fontWeight: 800, fontSize: '0.8rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Example Trigger Decisions (Right Now)</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
            {Object.entries(examples).map(([label, conf]) => (
              <ConfidenceCard key={label} label={label} conf={conf} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SourceReliabilityRow({ name, info }) {
  const badge = info.badge || 'unknown';
  const colors = BADGE_COLORS[badge] || BADGE_COLORS.unknown;
  const score = Math.round((info.reliability_score || 0) * 100);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', background: 'var(--white)', borderRadius: '12px', border: '1.5px solid var(--border)' }}>
      <div style={{ width: 10, height: 10, borderRadius: '50%', background: colors.dot || colors.color, flexShrink: 0 }} />
      <div style={{ flex: 1, fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-dark)' }}>{name}</div>
      <span style={{ fontSize: '0.72rem', fontWeight: 700, padding: '2px 8px', borderRadius: '8px', background: colors.bg, color: colors.color }}>{badge.toUpperCase()}</span>
      {info.staleness_seconds != null && (
        <span style={{ fontSize: '0.72rem', color: 'var(--text-light)' }}>{Math.round(info.staleness_seconds)}s ago</span>
      )}
      <div style={{ width: 80 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '2px', color: 'var(--text-light)' }}>
          <span>reliability</span><span style={{ fontWeight: 700, color: score >= 80 ? 'var(--green-primary)' : '#f59e0b' }}>{score}%</span>
        </div>
        <div style={{ height: 5, background: 'var(--gray-bg)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ width: `${score}%`, height: '100%', background: score >= 80 ? 'var(--green-primary)' : '#f59e0b', borderRadius: 3 }} />
        </div>
      </div>
    </div>
  );
}

function ConfidenceCard({ label, conf }) {
  const decision = conf.decision || 'hold';
  const dc = DECISION_COLORS[decision] || DECISION_COLORS.hold;
  const confPct = Math.round((conf.trigger_confidence_score || 0) * 100);
  const agreePct = Math.round((conf.agreement_score || 0) * 100);

  return (
    <div style={{ padding: '1rem', background: 'var(--white)', borderRadius: '14px', border: '1.5px solid var(--border)', borderTop: `3px solid ${dc.color}` }}>
      <div style={{ fontWeight: 800, fontSize: '0.82rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
        {label.replace(/_/g, ' ')}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '1.25rem' }}>{dc.icon}</span>
        <span style={{ fontWeight: 900, fontSize: '0.9rem', padding: '2px 10px', borderRadius: '8px', background: dc.bg, color: dc.color }}>
          {decision.replace(/_/g, ' ').toUpperCase()}
        </span>
      </div>
      <div style={{ fontSize: '0.78rem', color: 'var(--text-mid)', marginBottom: '0.75rem' }}>{conf.reason}</div>
      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.78rem' }}>
        <div>
          <div style={{ color: 'var(--text-light)', fontWeight: 700, marginBottom: '2px' }}>Confidence</div>
          <div style={{ fontWeight: 900, color: confPct >= 70 ? 'var(--green-primary)' : '#f59e0b' }}>{confPct}%</div>
        </div>
        <div>
          <div style={{ color: 'var(--text-light)', fontWeight: 700, marginBottom: '2px' }}>Agreement</div>
          <div style={{ fontWeight: 900, color: agreePct >= 80 ? 'var(--green-primary)' : '#f59e0b' }}>{agreePct}%</div>
        </div>
      </div>
    </div>
  );
}

// ── Sources tab ───────────────────────────────────────────────────────────────

function SourcesTab({ liveData }) {
  const sources = liveData?.data_sources || {};
  if (Object.keys(sources).length === 0)
    return <p style={{ color: 'var(--text-light)' }}>No source data yet — click Refresh.</p>;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem' }}>
      {Object.entries(sources).map(([name, info]) => {
        const status = info.status || 'unknown';
        const colors = BADGE_COLORS[status] || BADGE_COLORS.unknown;
        return (
          <div key={name} style={{ padding: '1rem', background: 'var(--white)', borderRadius: '14px', border: '1.5px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: colors.dot || colors.color }} />
              <span style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dark)' }}>{name}</span>
            </div>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, padding: '2px 8px', borderRadius: '8px', background: colors.bg, color: colors.color }}>
              {status.toUpperCase()}
            </span>
            {info.last_check && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.72rem', color: 'var(--text-light)' }}>
                Last check: {new Date(info.last_check).toLocaleTimeString()}
              </div>
            )}
            {info.last_success && (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-light)' }}>
                Last success: {new Date(info.last_success).toLocaleTimeString()}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Activity tab ──────────────────────────────────────────────────────────────

function ActivityTab({ liveData }) {
  const pa = liveData?.platform_activity;
  if (!pa) return <p style={{ color: 'var(--text-light)' }}>No activity data yet — click Refresh.</p>;

  const { total_sampled, active_on_platform, inactive_on_platform, partners } = pa;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Summary chips */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        {[
          { label: 'Sampled', value: total_sampled, color: 'var(--primary)' },
          { label: 'Active', value: active_on_platform, color: 'var(--green-primary)' },
          { label: 'Inactive', value: inactive_on_platform, color: 'var(--error)' },
        ].map(m => (
          <div key={m.label} style={{ flex: 1, minWidth: 100, padding: '0.875rem', borderRadius: '14px', background: 'var(--white)', border: `2px solid ${m.color}25`, textAlign: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 900, color: m.color, fontFamily: 'Nunito' }}>{m.value}</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-light)', fontWeight: 700, textTransform: 'uppercase' }}>{m.label}</div>
          </div>
        ))}
      </div>

      {/* Partner rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <p style={{ fontWeight: 800, fontSize: '0.78rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Partner Activity Snapshot</p>
        {(partners || []).map(p => (
          <ActivityRow key={p.partner_id} partner={p} />
        ))}
      </div>
    </div>
  );
}

function ActivityRow({ partner }) {
  const active = partner.active_shift && partner.platform_logged_in;
  const score = Math.round((partner.platform_score || 0) * 100);
  const scoreColor = score >= 80 ? 'var(--green-primary)' : score >= 50 ? '#f59e0b' : 'var(--error)';

  const PLATFORM_ICONS = { zomato: '🍕', swiggy: '🛵', zepto: '⚡', blinkit: '⚡' };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', background: 'var(--white)', borderRadius: '12px', border: '1.5px solid var(--border)', borderLeft: `4px solid ${active ? 'var(--green-primary)' : 'var(--error)'}` }}>
      <span style={{ fontSize: '1.25rem', flexShrink: 0 }}>{PLATFORM_ICONS[partner.platform] || '📱'}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dark)' }}>{partner.partner_name}</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-light)' }}>
          {partner.platform} · {partner.orders_completed_recent} orders
        </div>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <span style={{ fontSize: '0.72rem', fontWeight: 700, padding: '2px 8px', borderRadius: '8px', background: active ? '#dcfce7' : '#fef2f2', color: active ? '#166534' : '#991b1b' }}>
          {active ? '● ACTIVE' : '○ OFFLINE'}
        </span>
        <span style={{ fontSize: '0.78rem', fontWeight: 800, color: scoreColor }}>{score}%</span>
      </div>
    </div>
  );
}

// ── Zone data tab ─────────────────────────────────────────────────────────────

function ZoneTab({ zones, selectedZone, setSelectedZone, zoneData, liveData }) {
  const data = zoneData || liveData;
  return (
    <div>
      <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <select
          value={selectedZone}
          onChange={e => setSelectedZone(e.target.value)}
          style={{ padding: '0.5rem 0.75rem', borderRadius: '8px', border: '1.5px solid var(--border)', fontSize: '0.9rem', fontWeight: 600 }}
        >
          {zones.map(z => <option key={z.code} value={z.code}>{z.code} — {z.name}</option>)}
        </select>
      </div>

      {data && data.weather && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
          <DataCard title="Weather" icon="🌤️" source={data.weather?.source}>
            <Metric label="Temperature" value={data.weather?.temp_celsius} unit="°C" />
            <Metric label="Rainfall" value={data.weather?.rainfall_mm_hr} unit="mm/hr" />
            <Metric label="Humidity" value={data.weather?.humidity} unit="%" />
          </DataCard>
          <DataCard title="Air Quality" icon="💨" source={data.aqi?.source}>
            <Metric label="AQI" value={data.aqi?.aqi} />
            <Metric label="PM2.5" value={data.aqi?.pm25} unit="μg/m³" />
            <Metric label="Category" value={data.aqi?.category} />
          </DataCard>
          <DataCard title="Platform Status" icon="🏪" source={data.platform?.source}>
            <Metric label="Store" value={data.platform?.is_open ? '✅ Open' : '❌ Closed'} />
            {data.platform?.closure_reason && <Metric label="Reason" value={data.platform.closure_reason} />}
          </DataCard>
          <DataCard title="Civic Status" icon="🚨" source={data.shutdown?.source}>
            <Metric label="Shutdown" value={data.shutdown?.is_active ? '⚠️ Active' : '✅ Normal'} />
            {data.shutdown?.reason && <Metric label="Reason" value={data.shutdown.reason} />}
          </DataCard>
        </div>
      )}
      {!data?.weather && <p style={{ color: 'var(--text-light)' }}>Select a zone and click Refresh to load data.</p>}
    </div>
  );
}

function DataCard({ title, icon, source, children }) {
  const sourceColor = source === 'live' ? '#22c55e' : source === 'mock' ? '#f59e0b' : '#94a3b8';
  return (
    <div style={{ background: 'var(--white)', borderRadius: '16px', border: '1.5px solid var(--border)', padding: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.25rem' }}>{icon}</span>
          <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>{title}</span>
        </div>
        {source && (
          <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '2px 8px', borderRadius: '8px', background: `${sourceColor}20`, color: sourceColor }}>
            {source}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

function Metric({ label, value, unit }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
      <span style={{ fontSize: '0.8rem', color: 'var(--text-light)' }}>{label}</span>
      <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-dark)' }}>
        {value ?? '—'}{unit && <span style={{ color: 'var(--text-light)', fontWeight: 400 }}> {unit}</span>}
      </span>
    </div>
  );
}

function Spinner() {
  return <span style={{ width: 14, height: 14, border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite', display: 'inline-block' }} />;
}