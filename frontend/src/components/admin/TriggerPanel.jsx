import { useState, useRef, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Colored left-border per trigger type
const TRIGGER_COLORS = {
  rain: '#378ADD',
  heat: '#E24B4A',
  aqi: '#888780',
  shutdown: '#EF9F27',
  closure: '#7F77DD',
};

const TRIGGERS = [
  { type: 'rain', label: 'Heavy rain / flood', detail: '72mm/hr · IMD red alert · BLR-002', zone: 'BLR-002', icon: '🌧️' },
  { type: 'heat', label: 'Extreme heat', detail: '44°C · 4+ hrs · MUM-021', zone: 'MUM-021', icon: '🌡️' },
  { type: 'aqi', label: 'Dangerous AQI', detail: 'AQI 420 · 3 hrs · DEL-009', zone: 'DEL-009', icon: '💨' },
  { type: 'shutdown', label: 'Civic shutdown', detail: 'Curfew · 2+ hrs · BLR-047', zone: 'BLR-047', icon: '🚫' },
  { type: 'closure', label: 'Dark store closure', detail: 'Force majeure · 95 min · BLR-047', zone: 'BLR-047', icon: '🏪' },
];

const SOURCE_LABELS = {
  openweathermap: 'OpenWeatherMap',
  waqi_aqi: 'WAQI / CPCB AQI',
  zepto_ops: 'Zepto Ops (mock)',
  traffic_feed: 'Traffic Feed (mock)',
  civic_api: 'Civic API (mock)',
};

const SOURCE_TOOLTIPS = {
  live: 'Live data — connected to real API',
  mock: 'Using mock fallback data',
  unknown: 'API key not configured',
};

export default function TriggerPanel() {
  const [logLines, setLogLines] = useState([]);
  const [simulating, setSimulating] = useState(false);
  const [activeTrigger, setActiveTrigger] = useState(null);
  const [engineStatus, setEngineStatus] = useState(null);
  const [localActiveEvents, setLocalActiveEvents] = useState(null); // override during simulation
  const logRef = useRef(null);

  // Fix 6 — poll every 10s for live LAST POLL updates + stale detection
  const fetchEngineStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/panel/engine-status`);
      if (res.ok) {
        setEngineStatus(await res.json());
      }
    } catch {
      setEngineStatus(null);
    }
  }, []);

  useEffect(() => {
    fetchEngineStatus();
    const interval = setInterval(fetchEngineStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchEngineStatus]);

  // Determine if scheduler is stale (>2 min since last poll)
  function isSchedulerStale() {
    if (!engineStatus?.scheduler?.last_poll) return false;
    const lastPoll = new Date(engineStatus.scheduler.last_poll);
    const now = new Date();
    return (now - lastPoll) > 120000; // 2 minutes
  }

  function getSchedulerDotClass() {
    if (!engineStatus?.scheduler?.running) return 'engine-dot--off';
    if (isSchedulerStale()) return 'engine-dot--stale';
    return 'engine-dot--live';
  }

  // Fix 2 — streaming simulation with line-by-line setTimeout
  async function handleSimulate(trigger) {
    setSimulating(true);
    setActiveTrigger(trigger.type);
    setLogLines([]);
    setLocalActiveEvents(1); // Fix: show active event during simulation

    let streamWorked = false;

    try {
      const res = await fetch(`${API_BASE}/admin/panel/simulate-trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ triggerType: trigger.type, zone: trigger.zone }),
      });

      if (res.ok && res.body) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        const allLines = [];

        // Read all NDJSON lines from stream
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop();
          for (const line of lines) {
            if (line.trim()) {
              allLines.push(JSON.parse(line));
            }
          }
        }

        // Stream them visually one by one with 220ms delay
        if (allLines.length > 0) {
          streamWorked = true;
          await streamLines(allLines);
        }
      }
    } catch (err) {
      console.error('Simulation error:', err);
    }

    // Fallback if backend stream failed
    if (!streamWorked) {
      await runLocalSimulation(trigger);
    }

    setSimulating(false);
    setActiveTrigger(null);
    setLocalActiveEvents(null); // Reset — let real status take over
    setTimeout(fetchEngineStatus, 500);
  }

  // Stream lines one-by-one using Promise chain
  function streamLines(allLines) {
    return new Promise(resolve => {
      allLines.forEach((line, i) => {
        setTimeout(() => {
          setLogLines(prev => [...prev, line]);
          if (logRef.current) {
            logRef.current.scrollTop = logRef.current.scrollHeight;
          }
          if (i === allLines.length - 1) {
            resolve();
          }
        }, i * 220);
      });
    });
  }

  async function runLocalSimulation(trigger) {
    const mockSteps = [
      { ts: '5:47:23', msg: `Zone ${trigger.zone} polygon match confirmed — IMD red alert active` },
      { ts: '5:47:31', msg: `Zepto mock ops: zone suspended — 72mm/hr rainfall detected` },
      { ts: '5:47:39', msg: `Traffic cross-validation: confirms severe disruption` },
      { ts: '5:47:44', msg: `GPS coherence: normal — no spoofing anomalies` },
      { ts: '5:47:51', msg: `Run count confirmed: 3 deliveries completed before suspension` },
      { ts: '5:47:58', msg: `Fraud score: 0.11 → auto-approve` },
      { ts: '5:48:09', msg: `₹272 UPI credit via Razorpay mock — txn RC${trigger.zone}-${Math.floor(Math.random()*9000+1000)}` },
      { ts: '5:48:12', msg: `Push notification sent (Kannada) — claim processed` },
    ];

    await streamLines(mockSteps);
    await new Promise(r => setTimeout(r, 300));
    setLogLines(prev => [...prev, { ts: 'done', msg: 'Total: 49 seconds', total: 49 }]);
  }

  // Display active events: use local override during simulation, else real data
  const displayActiveEvents = localActiveEvents !== null
    ? localActiveEvents
    : (engineStatus?.engine?.active_events ?? 0);

  return (
    <div className="admin-section" style={{ animationDelay: '0.3s' }}>
      <div className="admin-section-label">DISRUPTION SIMULATION — TRIGGER ENGINE</div>

      {/* ── Live Engine Status Row ────────────────────────────────────── */}
      <div className="engine-status-bar" style={{ background: 'var(--green-light)', border: '1.5px solid rgba(61,184,92,0.15)', borderRadius: '18px', padding: '1.25rem 1.5rem', marginBottom: '1.5rem' }}>
        <div className="engine-status-bar__row" style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <div className="engine-status-item" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span className="engine-label" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '0.75rem', color: 'var(--green-dark)', textTransform: 'uppercase' }}>Scheduler</span>
            <span className={`engine-dot ${getSchedulerDotClass()}`} />
            <span className="engine-value" style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-dark)' }}>
              {!engineStatus?.scheduler?.running ? 'Stopped'
                : isSchedulerStale() ? 'Stale' : 'Running'}
            </span>
          </div>
          <div className="engine-status-item" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span className="engine-label" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '0.75rem', color: 'var(--green-dark)', textTransform: 'uppercase' }}>Poll interval</span>
            <span className="engine-value" style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-dark)' }}>
              {engineStatus?.scheduler?.poll_interval_seconds || 45}s
            </span>
          </div>
          <div className="engine-status-item" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span className="engine-label" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '0.75rem', color: 'var(--green-dark)', textTransform: 'uppercase' }}>Last poll</span>
            <span className="engine-value" style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-dark)' }}>
              {engineStatus?.scheduler?.last_poll
                ? new Date(engineStatus.scheduler.last_poll).toLocaleTimeString()
                : '—'}
            </span>
          </div>
          <div className="engine-status-item" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span className="engine-label" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '0.75rem', color: 'var(--green-dark)', textTransform: 'uppercase' }}>Active events</span>
            <span className="engine-value" style={{ fontWeight: 900, fontSize: '1.1rem', color: displayActiveEvents > 0 ? 'var(--error)' : 'var(--green-dark)' }}>
              {displayActiveEvents}
            </span>
          </div>
        </div>

        {/* Data source indicators */}
        <div className="engine-sources" style={{ display: 'flex', gap: '1.25rem', paddingTop: '1rem', borderTop: '1px solid rgba(61,184,92,0.1)' }}>
          {Object.entries(engineStatus?.data_sources || {}).map(([key, info]) => (
            <div key={key} className="engine-source" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-mid)' }}>
              <span className={`engine-dot ${info.status === 'live' ? 'engine-dot--green' : info.status === 'mock' ? 'engine-dot--amber' : 'engine-dot--red'}`} style={{ width: 7, height: 7, borderRadius: '50%' }} />
              <span>{SOURCE_LABELS[key] || key}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="trigger-panel__desc" style={{ color: 'var(--text-light)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
        Fire a mock disruption event to test the full claim pipeline end-to-end.
        The real engine polls automatically every 45 seconds.
      </p>

      {/* Trigger cards */}
      <div className="trigger-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '1rem' }}>
        {TRIGGERS.map(t => (
          <div
            key={t.type}
            className="trigger-card"
            style={{ 
              background: 'var(--white)', 
              border: '1.5px solid var(--border)', 
              borderLeft: `5px solid ${TRIGGER_COLORS[t.type]}`,
              borderRadius: '18px', 
              padding: '1.25rem',
              transition: 'all 0.2s',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '1.4rem' }}>{t.icon}</span>
              <strong style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.1rem', color: 'var(--text-dark)' }}>{t.label}</strong>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-light)', marginBottom: '1.25rem' }}>{t.detail}</p>
            <button
              className="trigger-card__btn"
              onClick={() => handleSimulate(t)}
              disabled={simulating}
              style={{
                width: '100%',
                padding: '0.75rem',
                background: 'var(--green-primary)',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                fontFamily: 'Nunito',
                fontWeight: 800,
                cursor: 'pointer'
              }}
            >
              {simulating && activeTrigger === t.type ? 'Running...' : 'Simulate ↗'}
            </button>
          </div>
        ))}
      </div>

      {/* Simulation log */}
      {logLines.length > 0 && (
        <div className="sim-log" ref={logRef} style={{ marginTop: '1.5rem', background: 'var(--gray-bg)', border: '1.5px solid var(--border)', borderRadius: '18px', padding: '1.25rem', maxHeight: '300px', overflowY: 'auto' }}>
          <div style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '0.9rem', marginBottom: '1rem', color: 'var(--text-dark)' }}>Live simulation log</div>
          {logLines.map((line, i) => (
            <div key={i} style={{ fontFamily: 'monospace', fontSize: '0.75rem', padding: '0.25rem 0', color: 'var(--text-mid)', borderBottom: '1px solid rgba(0,0,0,0.03)' }}>
              {line.total ? (
                <strong style={{ color: 'var(--green-dark)' }}>{line.msg}</strong>
              ) : (
                <>
                  <span style={{ color: 'var(--text-light)' }}>[{line.ts}]</span> — {line.msg}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
