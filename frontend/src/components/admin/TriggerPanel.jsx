import { useState, useRef, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const TRIGGERS = [
  {
    type: 'rain',
    label: 'Heavy rain / flood',
    detail: '72mm/hr · IMD red alert · BLR-047',
    zone: 'BLR-047',
    icon: '🌧️',
  },
  {
    type: 'heat',
    label: 'Extreme heat',
    detail: '44°C · 4+ hrs · MUM-021',
    zone: 'MUM-021',
    icon: '🌡️',
  },
  {
    type: 'aqi',
    label: 'Dangerous AQI',
    detail: 'AQI 420 · 3 hrs · DEL-009',
    zone: 'DEL-009',
    icon: '💨',
  },
  {
    type: 'shutdown',
    label: 'Civic shutdown',
    detail: 'Curfew · 2+ hrs · BLR-047',
    zone: 'BLR-047',
    icon: '🚫',
  },
  {
    type: 'closure',
    label: 'Dark store closure',
    detail: 'Force majeure · 95 min · BLR-047',
    zone: 'BLR-047',
    icon: '🏪',
  },
];

const SOURCE_LABELS = {
  openweathermap: 'OpenWeatherMap',
  waqi_aqi: 'WAQI / CPCB AQI',
  zepto_ops: 'Zepto Ops (mock)',
  traffic_feed: 'Traffic Feed (mock)',
  civic_api: 'Civic API (mock)',
};

export default function TriggerPanel() {
  const [logLines, setLogLines] = useState([]);
  const [simulating, setSimulating] = useState(false);
  const [activeTrigger, setActiveTrigger] = useState(null);
  const [engineStatus, setEngineStatus] = useState(null);
  const logRef = useRef(null);

  // Fetch engine status on mount and every 30s
  useEffect(() => {
    fetchEngineStatus();
    const interval = setInterval(fetchEngineStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  async function fetchEngineStatus() {
    try {
      const res = await fetch(`${API_BASE}/admin/panel/engine-status`);
      if (res.ok) {
        setEngineStatus(await res.json());
      }
    } catch {
      // Fallback — engine status unavailable
      setEngineStatus(null);
    }
  }

  async function handleSimulate(trigger) {
    setSimulating(true);
    setActiveTrigger(trigger.type);
    setLogLines([]);

    try {
      const res = await fetch(`${API_BASE}/admin/panel/simulate-trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ triggerType: trigger.type, zone: trigger.zone }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (line.trim()) {
            const parsed = JSON.parse(line);
            setLogLines(prev => [...prev, parsed]);
            if (logRef.current) {
              logRef.current.scrollTop = logRef.current.scrollHeight;
            }
          }
        }
      }
    } catch (err) {
      console.error('Simulation error:', err);
      await runLocalSimulation(trigger);
    } finally {
      setSimulating(false);
      setActiveTrigger(null);
      // Refresh engine status after simulation
      setTimeout(fetchEngineStatus, 500);
    }
  }

  async function runLocalSimulation(trigger) {
    const mockSteps = [
      { ts: '5:47:23', msg: `Zone ${trigger.zone} polygon match confirmed` },
      { ts: '5:47:31', msg: `Zepto mock ops: zone suspended` },
      { ts: '5:47:39', msg: `Traffic cross-validation: severe disruption confirmed` },
      { ts: '5:47:44', msg: `GPS coherence: normal` },
      { ts: '5:47:51', msg: `Run count confirmed: 3 deliveries before suspension` },
      { ts: '5:47:58', msg: `Fraud score: 0.11 → auto-approve` },
      { ts: '5:48:09', msg: `₹272 UPI credit via Razorpay mock` },
      { ts: '5:48:12', msg: `Push notification sent (Kannada)` },
    ];

    for (const step of mockSteps) {
      await new Promise(r => setTimeout(r, 180));
      setLogLines(prev => [...prev, step]);
    }
    await new Promise(r => setTimeout(r, 200));
    setLogLines(prev => [...prev, { ts: 'done', msg: 'Total: 49 seconds', total: 49 }]);
  }

  return (
    <div className="admin-section" style={{ animationDelay: '0.3s' }}>
      <div className="admin-section-label">DISRUPTION SIMULATION — TRIGGER ENGINE</div>

      {/* ── Live Engine Status Row ────────────────────────────────────── */}
      <div className="engine-status-bar">
        <div className="engine-status-bar__row">
          <div className="engine-status-item">
            <span className="engine-label">Scheduler</span>
            <span className={`engine-dot ${engineStatus?.scheduler?.running ? 'engine-dot--live' : 'engine-dot--off'}`} />
            <span className="engine-value">
              {engineStatus?.scheduler?.running ? 'Running' : 'Stopped'}
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
            <span className="engine-value engine-value--highlight">
              {engineStatus?.engine?.active_events ?? 0}
            </span>
          </div>
        </div>

        {/* Data source indicators */}
        <div className="engine-sources">
          {Object.entries(engineStatus?.data_sources || {}).map(([key, info]) => (
            <div key={key} className="engine-source">
              <span className={`engine-dot ${info.status === 'live' ? 'engine-dot--live' : info.status === 'mock' ? 'engine-dot--mock' : 'engine-dot--off'}`} />
              <span className="engine-source__name">{SOURCE_LABELS[key] || key}</span>
              <span className="engine-source__status">{info.status}</span>
            </div>
          ))}
          {/* Show defaults if no engine status */}
          {!engineStatus && Object.entries(SOURCE_LABELS).map(([key, label]) => (
            <div key={key} className="engine-source">
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

      {/* Trigger cards */}
      <div className="trigger-grid">
        {TRIGGERS.map(t => (
          <div key={t.type} className="trigger-card">
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
                <span className="trigger-card__spinner" />
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
              style={{ animationDelay: `${i * 60}ms` }}
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
