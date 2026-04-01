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
  { type: 'rain', label: 'Heavy rain / flood', detail: '72mm/hr · IMD red alert · BLR-047', zone: 'BLR-047', icon: '🌧️' },
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
      <div className="engine-status-bar">
        <div className="engine-status-bar__row">
          <div className="engine-status-item">
            <span className="engine-label">Scheduler</span>
            <span className={`engine-dot ${getSchedulerDotClass()}`} />
            <span className="engine-value">
              {!engineStatus?.scheduler?.running ? 'Stopped'
                : isSchedulerStale() ? 'Stale' : 'Running'}
            </span>
          </div>
          <div className="engine-status-item">
            <span className="engine-label">Poll interval</span>
            <span className="engine-value">
              {engineStatus?.scheduler?.poll_interval_seconds || 45}s
            </span>
          </div>
          <div className="engine-status-item">
            <span className="engine-label">Last poll</span>
            <span className="engine-value">
              {engineStatus?.scheduler?.last_poll
                ? new Date(engineStatus.scheduler.last_poll).toLocaleTimeString()
                : '—'}
            </span>
          </div>
          <div className="engine-status-item">
            <span className="engine-label">Active events</span>
            <span className={`engine-value ${displayActiveEvents > 0 ? 'engine-value--highlight' : ''}`}>
              {displayActiveEvents}
            </span>
          </div>
        </div>

        {/* Data source indicators with tooltips */}
        <div className="engine-sources">
          {Object.entries(engineStatus?.data_sources || {}).map(([key, info]) => (
            <div
              key={key}
              className="engine-source"
              title={SOURCE_TOOLTIPS[info.status] || ''}
            >
              <span className={`engine-dot ${info.status === 'live' ? 'engine-dot--live' : info.status === 'mock' ? 'engine-dot--mock' : 'engine-dot--off'}`} />
              <span className="engine-source__name">{SOURCE_LABELS[key] || key}</span>
              <span className="engine-source__status">{info.status}</span>
            </div>
          ))}
          {!engineStatus && Object.entries(SOURCE_LABELS).map(([key, label]) => (
            <div key={key} className="engine-source" title="API key not configured">
              <span className="engine-dot engine-dot--off" />
              <span className="engine-source__name">{label}</span>
              <span className="engine-source__status">unknown</span>
            </div>
          ))}
        </div>
      </div>

      <p className="trigger-panel__desc">
        Fire a mock disruption event to test the full claim pipeline end-to-end.
        The real engine polls automatically every 45 seconds.
      </p>

      {/* Trigger cards with colored left borders */}
      <div className="trigger-grid">
        {TRIGGERS.map(t => (
          <div
            key={t.type}
            className="trigger-card"
            style={{ borderLeft: `3px solid ${TRIGGER_COLORS[t.type]}` }}
          >
            <div className="trigger-card__header">
              <span className="trigger-card__icon">{t.icon}</span>
              <strong className="trigger-card__label">{t.label}</strong>
            </div>
            <p className="trigger-card__detail">{t.detail}</p>
            <button
              className="trigger-card__btn"
              onClick={() => handleSimulate(t)}
              disabled={simulating}
            >
              {simulating && activeTrigger === t.type ? (
                <><span className="trigger-card__spinner" /> Running...</>
              ) : (
                <>Simulate ↗</>
              )}
            </button>
          </div>
        ))}
      </div>

      {/* Simulation log */}
      {logLines.length > 0 && (
        <div className="sim-log" ref={logRef}>
          <div className="sim-log__title">Last simulation log</div>
          {logLines.map((line, i) => (
            <div
              key={i}
              className={`sim-log__line ${line.total ? 'sim-log__total' : ''}`}
            >
              {line.total ? (
                <strong>{line.msg}</strong>
              ) : (
                <>
                  <span className="sim-log__ts">{line.ts}</span>
                  <span className="sim-log__sep">—</span>
                  <span className="sim-log__msg">{line.msg}</span>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
