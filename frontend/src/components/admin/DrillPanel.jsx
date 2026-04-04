// frontend/src/components/admin/DrillPanel.jsx
// Structured drill execution panel with preset selection and real-time timeline

import { useState, useEffect, useRef } from 'react';
import DrillTimeline from './DrillTimeline';
import ImpactPanel from './ImpactPanel';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const DRILL_PRESETS = [
  { type: 'flash_flood', label: 'Flash Flood', icon: '🌊', description: 'Heavy rainfall 72mm/hr' },
  { type: 'aqi_spike', label: 'AQI Spike', icon: '💨', description: 'Hazardous AQI 450' },
  { type: 'heatwave', label: 'Heatwave', icon: '🌡️', description: 'Extreme heat 46°C' },
  { type: 'store_closure', label: 'Store Closure', icon: '🏪', description: 'Dark store force majeure' },
  { type: 'curfew', label: 'Curfew', icon: '🚫', description: 'Civic shutdown order' },
  // Phase 2 Team Guide Stress Scenarios
  { type: 'monsoon_14day', label: '14-Day Monsoon', icon: '🌧️', description: 'Sustained monsoon (BLR+BOM), 70% payout', stress: true },
  { type: 'multi_city_aqi', label: 'Multi-City AQI', icon: '🏭', description: 'NCR AQI spike (DEL+NOI+GGN)', stress: true },
  { type: 'cyclone', label: 'Cyclone', icon: '🌀', description: 'Cyclone (CHN+BOM), rain + shutdown', stress: true },
  { type: 'bandh', label: 'Bandh', icon: '✊', description: 'City-wide strike, all stores closed', stress: true },
  { type: 'collusion_fraud', label: 'Fraud Test', icon: '🕵️', description: 'Collusion ring detection test', stress: true },
];

const PRESET_COLORS = {
  flash_flood: '#378ADD',
  aqi_spike: '#888780',
  heatwave: '#E24B4A',
  store_closure: '#7F77DD',
  curfew: '#EF9F27',
  // Stress scenarios
  monsoon_14day: '#2E7D32',
  multi_city_aqi: '#5D4037',
  cyclone: '#0D47A1',
  bandh: '#C62828',
  collusion_fraud: '#6A1B9A',
};

export default function DrillPanel({ onZoneSelect }) {
  const [selectedPreset, setSelectedPreset] = useState('flash_flood');
  const [selectedZone, setSelectedZone] = useState(null);
  const [zones, setZones] = useState([]);
  const [forceMode, setForceMode] = useState(true);
  const [simulateSustained, setSimulateSustained] = useState(false);
  const [drillId, setDrillId] = useState(null);
  const [drillStatus, setDrillStatus] = useState(null);
  const [timelineEvents, setTimelineEvents] = useState([]);
  const [impactData, setImpactData] = useState(null);
  const [running, setRunning] = useState(false);
  const [history, setHistory] = useState([]);

  // Fetch zones for dropdown
  useEffect(() => {
    fetchZones();
    fetchHistory();
  }, []);

  async function fetchZones() {
    try {
      const res = await fetch(`${API_BASE}/zones`);
      if (res.ok) {
        const data = await res.json();
        setZones(data);
        if (data.length > 0 && !selectedZone) {
          setSelectedZone(data[0].code);
        }
      }
    } catch {
      // Fallback demo zones
      setZones([
        { code: 'BLR-047', name: 'Koramangala' },
        { code: 'MUM-021', name: 'Andheri East' },
        { code: 'DEL-009', name: 'Connaught Place' },
      ]);
      setSelectedZone('BLR-047');
    }
  }

  async function fetchHistory() {
    try {
      const res = await fetch(`${API_BASE}/admin/panel/drills/history?limit=10`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.drills || []);
      }
    } catch {
      // Ignore
    }
  }

  async function runDrill() {
    if (!selectedZone) return;

    setRunning(true);
    setDrillId(null);
    setDrillStatus(null);
    setTimelineEvents([]);
    setImpactData(null);

    try {
      const res = await fetch(`${API_BASE}/admin/panel/drills/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          drill_type: selectedPreset,
          zone_code: selectedZone,
          force: forceMode,
          simulate_sustained_days: simulateSustained ? 5 : 0,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setDrillId(data.drill_id);
        setDrillStatus(data.status);

        // Stream events
        await streamDrillEvents(data.drill_id);

        // Fetch impact
        await fetchImpact(data.drill_id);
      }
    } catch (err) {
      console.error('Drill error:', err);
    }

    setRunning(false);
    fetchHistory();
  }

  async function streamDrillEvents(id) {
    try {
      const res = await fetch(`${API_BASE}/admin/panel/drills/${id}/stream`);
      if (!res.ok || !res.body) return;

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
            try {
              const event = JSON.parse(line);
              setTimelineEvents(prev => [...prev, event]);
            } catch {
              // Skip invalid JSON
            }
          }
        }
      }
    } catch {
      // Fallback handled
    }
  }

  async function fetchImpact(id) {
    try {
      const res = await fetch(`${API_BASE}/admin/panel/drills/${id}/impact`);
      if (res.ok) {
        const data = await res.json();
        setImpactData(data);
      }
    } catch {
      // Ignore
    }
  }

  function handleZoneFromMap(zoneCode) {
    setSelectedZone(zoneCode);
  }

  // Expose zone selection for parent
  useEffect(() => {
    if (onZoneSelect) {
      onZoneSelect(handleZoneFromMap);
    }
  }, [onZoneSelect]);

  return (
    <section className="drill-panel">
      <div className="drill-panel__header" style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)' }}>
          🎯 Drill Execution
        </h2>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.4rem' }}>
          Run structured drills to verify the full claim pipeline end-to-end.
        </p>
      </div>

      {/* Drill configuration */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Preset selection */}
        <div style={{ background: 'var(--white)', borderRadius: '18px', border: '1.5px solid var(--border)', padding: '1.25rem' }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-light)', display: 'block', marginBottom: '0.75rem' }}>
            Drill Preset
          </label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {DRILL_PRESETS.map(preset => (
              <button
                key={preset.type}
                onClick={() => setSelectedPreset(preset.type)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.75rem 1rem',
                  borderRadius: '12px',
                  border: selectedPreset === preset.type ? `2px solid ${PRESET_COLORS[preset.type]}` : '1.5px solid var(--border)',
                  background: selectedPreset === preset.type ? `${PRESET_COLORS[preset.type]}10` : 'transparent',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s',
                }}
              >
                <span style={{ fontSize: '1.25rem' }}>{preset.icon}</span>
                <div>
                  <div style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>{preset.label}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-light)' }}>{preset.description}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Zone and options */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ background: 'var(--white)', borderRadius: '18px', border: '1.5px solid var(--border)', padding: '1.25rem' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-light)', display: 'block', marginBottom: '0.75rem' }}>
              Target Zone
            </label>
            <select
              value={selectedZone || ''}
              onChange={e => setSelectedZone(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '10px',
                border: '1.5px solid var(--border)',
                fontSize: '0.9rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {zones.map(z => (
                <option key={z.code} value={z.code}>
                  {z.code} — {z.name}
                </option>
              ))}
            </select>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-light)', marginTop: '0.5rem' }}>
              Or click a zone on the map to select it
            </p>
          </div>

          <div style={{ background: 'var(--white)', borderRadius: '18px', border: '1.5px solid var(--border)', padding: '1.25rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={forceMode}
                onChange={e => setForceMode(e.target.checked)}
                style={{ width: 18, height: 18 }}
              />
              <div>
                <div style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>Force Mode</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-light)' }}>Bypass duration requirements for immediate trigger</div>
              </div>
            </label>
          </div>

          <div style={{ background: 'var(--white)', borderRadius: '18px', border: simulateSustained ? '2px solid #2E7D32' : '1.5px solid var(--border)', padding: '1.25rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={simulateSustained}
                onChange={e => setSimulateSustained(e.target.checked)}
                style={{ width: 18, height: 18 }}
              />
              <div>
                <div style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>
                  Simulate Sustained Event (70% payout)
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-light)' }}>
                  Inject 5-day history → triggers sustained mode → 70% payout
                </div>
              </div>
            </label>
          </div>

          <button
            onClick={runDrill}
            disabled={running || !selectedZone}
            style={{
              padding: '1rem 2rem',
              borderRadius: '14px',
              background: running ? 'var(--text-light)' : 'var(--green-primary)',
              color: 'white',
              border: 'none',
              fontFamily: 'Nunito',
              fontWeight: 900,
              fontSize: '1rem',
              cursor: running ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
            }}
          >
            {running ? (
              <>
                <span className="drill-spinner" style={{ width: 16, height: 16, border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                Running Drill...
              </>
            ) : (
              <>Run Drill →</>
            )}
          </button>
        </div>
      </div>

      {/* Timeline and Impact */}
      {(timelineEvents.length > 0 || impactData) && (
        <div style={{ display: 'grid', gridTemplateColumns: impactData ? '1fr 400px' : '1fr', gap: '1.5rem' }}>
          {timelineEvents.length > 0 && (
            <DrillTimeline events={timelineEvents} drillId={drillId} />
          )}
          {impactData && (
            <ImpactPanel impact={impactData} />
          )}
        </div>
      )}

      {/* Recent history */}
      {history.length > 0 && !running && timelineEvents.length === 0 && (
        <div style={{ marginTop: '1.5rem' }}>
          <h3 style={{ fontFamily: 'Nunito', fontWeight: 800, fontSize: '1rem', color: 'var(--text-dark)', marginBottom: '1rem' }}>
            Recent Drills
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {history.slice(0, 5).map(drill => (
              <div
                key={drill.drill_id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.75rem 1rem',
                  background: 'var(--white)',
                  borderRadius: '12px',
                  border: '1.5px solid var(--border)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: drill.status === 'completed' ? 'var(--green-primary)' : drill.status === 'failed' ? 'var(--error)' : 'var(--warning)',
                  }} />
                  <div>
                    <code style={{ fontWeight: 700, fontSize: '0.85rem' }}>{drill.zone_code}</code>
                    <span style={{ color: 'var(--text-light)', margin: '0 0.5rem' }}>·</span>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-mid)' }}>{drill.drill_type.replace('_', ' ')}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.8rem', color: 'var(--text-light)' }}>
                  <span>{drill.claims_created} claims</span>
                  {drill.total_latency_ms && <span>{drill.total_latency_ms}ms</span>}
                  <span>{new Date(drill.started_at).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </section>
  );
}
