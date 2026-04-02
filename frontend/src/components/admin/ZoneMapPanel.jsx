// frontend/src/components/admin/ZoneMapPanel.jsx
// Zone density band visualization: colour-coded Low / Medium / High
// Sustained event flag indicator per zone
// No external map library needed -- SVG-based schematic map with real city coordinates

import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Demo zones -- replace with real API data when Person 1/2 wires the zones endpoint
const DEMO_ZONES = [
  // Bangalore
  { id: 'BLR-047', city: 'BLR', name: 'Koramangala',   density: 'High',   partners: 210, lr: 71, sustained: false, active_trigger: 'Rain',  x: 22, y: 62 },
  { id: 'BLR-031', city: 'BLR', name: 'Indiranagar',   density: 'Medium', partners: 120, lr: 58, sustained: false, active_trigger: null,    x: 24, y: 58 },
  { id: 'BLR-015', city: 'BLR', name: 'Whitefield',    density: 'Low',    partners: 45,  lr: 44, sustained: false, active_trigger: null,    x: 28, y: 60 },
  { id: 'BLR-089', city: 'BLR', name: 'Bellandur',     density: 'Medium', partners: 95,  lr: 82, sustained: true,  active_trigger: 'Rain',  x: 26, y: 64 },
  // Mumbai
  { id: 'MUM-021', city: 'MUM', name: 'Andheri East',  density: 'High',   partners: 180, lr: 54, sustained: false, active_trigger: null,    x: 12, y: 42 },
  { id: 'MUM-034', city: 'MUM', name: 'Dadar',         density: 'High',   partners: 195, lr: 79, sustained: true,  active_trigger: 'Rain',  x: 11, y: 46 },
  { id: 'MUM-008', city: 'MUM', name: 'Powai',         density: 'Low',    partners: 38,  lr: 41, sustained: false, active_trigger: null,    x: 13, y: 40 },
  // Delhi
  { id: 'DEL-009', city: 'DEL', name: 'Connaught Place',density:'Low',    partners: 42,  lr: 48, sustained: false, active_trigger: null,    x: 22, y: 22 },
  { id: 'DEL-044', city: 'DEL', name: 'Anand Vihar',   density: 'High',   partners: 165, lr: 91, sustained: true,  active_trigger: 'AQI',   x: 26, y: 20 },
  { id: 'DEL-067', city: 'DEL', name: 'Dwarka',        density: 'Medium', partners: 88,  lr: 62, sustained: false, active_trigger: null,    x: 19, y: 23 },
  // Chennai
  { id: 'CHN-011', city: 'CHN', name: 'T. Nagar',      density: 'High',   partners: 155, lr: 55, sustained: false, active_trigger: null,    x: 24, y: 78 },
  { id: 'CHN-029', city: 'CHN', name: 'Velachery',     density: 'Medium', partners: 90,  lr: 66, sustained: false, active_trigger: null,    x: 25, y: 80 },
];

const DENSITY_COLORS = {
  Low:    { fill: '#f1f5f1', stroke: '#1a2e1a', label: 'Low (<50)',     dot: 'var(--green-primary)' },
  Medium: { fill: '#fef9c3', stroke: '#d97706', label: 'Medium (50-150)', dot: 'var(--warning)' },
  High:   { fill: '#fee2e2', stroke: '#dc2626', label: 'High (>150)',   dot: 'var(--error)' },
};

function ZoneCircle({ zone, onSelect, selected }) {
  const dc = DENSITY_COLORS[zone.density];
  const r = zone.density === 'High' ? 3.2 : zone.density === 'Medium' ? 2.4 : 1.8;
  return (
    <g
      className="zone-circle-group"
      onClick={() => onSelect(zone)}
      style={{ cursor: 'pointer' }}
      aria-label={zone.name}
    >
      <circle
        cx={`${zone.x}%`} cy={`${zone.y}%`}
        r={r * 1.6 + '%'}
        fill={dc.fill}
        stroke={selected ? 'var(--green-primary)' : dc.stroke}
        strokeWidth={selected ? '0.4%' : '0.15%'}
        opacity={0.9}
      />
      {/* Pulsing ring for sustained event zones */}
      {zone.sustained && (
        <circle
          cx={`${zone.x}%`} cy={`${zone.y}%`}
          r={(r * 1.6 + 1) + '%'}
          fill="none"
          stroke="var(--error)"
          strokeWidth="0.15%"
          strokeDasharray="1%,0.5%"
          opacity={0.7}
        >
          <animate attributeName="stroke-dashoffset" values="0;-10%" dur="2s" repeatCount="indefinite" />
        </circle>
      )}
      {/* Sustained flag */}
      {zone.sustained && (
        <text x={`${zone.x + r * 1.8}%`} y={`${zone.y - r}%`} fontSize="1.6%" textAnchor="start" fill="var(--error)">{'\u26A1'}</text>
      )}
      {/* Active trigger */}
      {zone.active_trigger && (
        <text x={`${zone.x}%`} y={`${zone.y + r * 2.2}%`} fontSize="1.3%" textAnchor="middle" fill={dc.stroke} fontWeight="800" fontFamily="Nunito">
          {zone.active_trigger}
        </text>
      )}
    </g>
  );
}

export default function ZoneMapPanel() {
  const [zones, setZones] = useState(DEMO_ZONES);
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState('All');

  useEffect(() => {
    fetchZones();
    const t = setInterval(fetchZones, 20000);
    return () => clearInterval(t);
  }, []);

  async function fetchZones() {
    try {
      const res = await fetch(`${API_BASE}/admin/panel/zones`);
      if (res.ok) {
        const data = await res.json();
        if (data.zones?.length) setZones(data.zones);
      }
    } catch {
      // Use demo data
    }
  }

  const filteredZones = filter === 'All'
    ? zones
    : filter === 'Sustained'
    ? zones.filter(z => z.sustained)
    : zones.filter(z => z.density === filter);

  const sustainedCount = zones.filter(z => z.sustained).length;
  const highCount      = zones.filter(z => z.density === 'High').length;

  return (
    <section className="zone-map-panel">
      <div className="zone-map-panel__header" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 className="zone-map-panel__title" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)' }}>{'\u{1F5FA}'} Zone Map</h2>
          <p className="zone-map-panel__subtitle" style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.4rem' }}>
            Density bands &nbsp;&middot;&nbsp; {sustainedCount > 0 && <span className="zone-map-panel__sustained-count" style={{ color: 'var(--error)', fontWeight: 700 }}>{'\u26A1'} {sustainedCount} sustained events</span>}
            &nbsp;{highCount} high-density zones
          </p>
        </div>

        {/* Density filter */}
        <div 
          className="zone-map-filter" 
          style={{ 
            display: 'flex', 
            background: 'var(--white)', 
            padding: '0.3rem', 
            borderRadius: '12px', 
            border: '1.5px solid var(--border)',
            gap: '0.25rem'
          }}
        >
          {['All', 'Low', 'Medium', 'High', 'Sustained'].map(f => (
            <button
              key={f}
              className={`zone-map-filter__btn ${filter === f ? 'zone-map-filter__btn--active' : ''}`}
              onClick={() => setFilter(f)}
              style={{
                padding: '0.4rem 0.85rem',
                borderRadius: '8px',
                fontSize: '0.75rem',
                fontWeight: 800,
                border: 'none',
                cursor: 'pointer',
                fontFamily: 'Nunito',
                background: filter === f ? 'var(--green-primary)' : 'transparent',
                color: filter === f ? 'var(--white)' : 'var(--text-light)',
                transition: 'all 0.2s'
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="zone-map-body" style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '1.5rem', alignItems: 'start' }}>
        {/* SVG schematic map */}
        <div className="zone-map-svg-wrapper" style={{ background: 'var(--white)', borderRadius: '24px', border: '1.5px solid var(--border)', padding: '1rem', position: 'relative' }}>
          <svg
            viewBox="0 0 100 100"
            className="zone-map-svg"
            xmlns="http://www.w3.org/2000/svg"
            style={{ borderRadius: '18px' }}
          >
            {/* Background */}
            <rect width="100" height="100" fill="#f8fafc" rx="2" />

            {/* City labels */}
            {[
              { label: 'Delhi NCR', x: 22, y: 16 },
              { label: 'Bangalore', x: 22, y: 55 },
              { label: 'Mumbai',    x: 10, y: 37 },
              { label: 'Chennai',   x: 24, y: 74 },
            ].map(c => (
              <text key={c.label} x={`${c.x}%`} y={`${c.y}%`} fontSize="2.8%" fill="var(--text-light)" fontWeight="900" fontFamily="Nunito">
                {c.label}
              </text>
            ))}

            {/* Zone circles */}
            {filteredZones.map(z => (
              <ZoneCircle
                key={z.id}
                zone={z}
                onSelect={setSelected}
                selected={selected?.id === z.id}
              />
            ))}
          </svg>

          {/* Legend */}
          <div className="zone-map-legend" style={{ position: 'absolute', bottom: '2rem', right: '2rem', background: 'rgba(255,255,255,0.92)', backdropFilter: 'blur(4px)', padding: '1rem', borderRadius: '16px', border: '1.5px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {Object.entries(DENSITY_COLORS).map(([key, val]) => (
              <div key={key} className="zone-map-legend__item" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-mid)' }}>
                <span className="zone-map-legend__dot" style={{ background: val.dot, width: 10, height: 10, borderRadius: '50%' }} />
                {val.label}
              </div>
            ))}
            <div className="zone-map-legend__item" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-mid)' }}>
              <span className="zone-map-legend__icon">⚡</span> Sustained event
            </div>
          </div>
        </div>

        {/* Zone detail panel */}
        <div className="zone-detail-panel" style={{ background: 'var(--white)', border: '1.5px solid var(--border)', borderRadius: '24px', padding: '1.5rem', animation: 'fadeInUp 0.4s ease' }}>
          {selected ? (
            <div className="zone-detail">
              <div className="zone-detail__top" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
                <div>
                  <p className="zone-detail__name" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.4rem', color: 'var(--text-dark)' }}>{selected.name}</p>
                  <code className="zone-detail__code" style={{ fontSize: '0.8rem', background: 'var(--gray-bg)', padding: '0.3rem 0.6rem', borderRadius: '8px', color: 'var(--text-light)' }}>{selected.id}</code>
                </div>
                <button 
                  className="zone-detail__close" 
                  onClick={() => setSelected(null)}
                  style={{ background: 'var(--gray-bg)', border: 'none', width: 30, height: 30, borderRadius: '50%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                >
                    ✕
                </button>
              </div>

              <div className="zone-detail__stats" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.5rem' }}>
                {[
                  { l: 'Density Band', v: selected.density, cl: DENSITY_COLORS[selected.density].dot },
                  { l: 'Active Partners', v: selected.partners, cl: 'var(--text-dark)' },
                  { l: 'Loss Ratio', v: `${selected.lr}%`, cl: selected.lr > 85 ? 'var(--error)' : 'var(--green-primary)' },
                  { l: 'Active Trigger', v: selected.active_trigger || '--', cl: 'var(--text-dark)' }
                ].map(st => (
                  <div key={st.l} style={{ background: 'var(--gray-bg)', borderRadius: '14px', padding: '1rem', textAlign: 'center' }}>
                    <p style={{ fontSize: '0.65rem', color: 'var(--text-light)', fontWeight: 700, textTransform: 'uppercase' }}>{st.l}</p>
                    <p style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.15rem', color: st.cl, marginTop: '2px' }}>{st.v}</p>
                  </div>
                ))}
              </div>

              {selected.sustained && (
                <div 
                  className="zone-detail__sustained" 
                  style={{ 
                    background: '#fee2e2', 
                    border: '1.5px solid var(--error)', 
                    borderRadius: '16px', 
                    padding: '1rem', 
                    display: 'flex', 
                    gap: '0.75rem', 
                    alignItems: 'center', 
                    color: '#991b1b',
                    marginBottom: '1.5rem'
                  }}
                >
                  <span style={{ fontSize: '1.75rem' }}>⚡</span>
                  <div>
                    <strong style={{ fontSize: '0.9rem', display: 'block' }}>Sustained Event Active</strong>
                    <p style={{ fontSize: '0.75rem', margin: '0.2rem 0 0', lineHeight: 1.4 }}>Payout mode: 70% of tier/day, no weekly cap. Review required at Day 7.</p>
                  </div>
                </div>
              )}

              <div className="zone-detail__density-info" style={{ borderTop: '1.5px solid var(--border)', paddingTop: '1.25rem' }}>
                <p style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-mid)', marginBottom: '0.5rem' }}>DENSITY CAP FORMULA</p>
                <p 
                  className="zone-detail__density-formula" 
                  style={{ 
                    fontSize: '0.7rem', 
                    fontFamily: 'monospace', 
                    color: 'var(--text-light)', 
                    background: 'var(--gray-bg)', 
                    padding: '0.75rem', 
                    borderRadius: '10px',
                    lineHeight: 1.6
                  }}
                >
                  payout = min(tier_max, city_weekly / active_partners)<br />
                  weighted_density = (partners / avg_partners)
                </p>
              </div>
            </div>
          ) : (
            <div className="zone-detail zone-detail--empty" style={{ textAlign: 'center', padding: '2rem 0' }}>
              <p style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-mid)' }}>Select a zone</p>
              <p className="zone-detail__hint" style={{ fontSize: '0.8rem', color: 'var(--text-light)', marginTop: '0.5rem' }}>Click a circle on the map to see real-time zone health</p>
              <div className="zone-detail__summary" style={{ marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {['Low', 'Medium', 'High'].map(d => (
                  <div key={d} className="zone-detail__summary-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'var(--gray-bg)', borderRadius: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <span style={{ background: DENSITY_COLORS[d].dot, width: 8, height: 8, borderRadius: '50%' }} />
                      <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>{d}</span>
                    </div>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-mid)' }}>{zones.filter(z => z.density === d).length} zones</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
