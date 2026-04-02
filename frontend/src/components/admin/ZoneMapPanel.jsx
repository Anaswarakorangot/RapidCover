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
  Low:    { fill: '#d1fae5', stroke: '#059669', label: 'Low (<50)',     dot: '#059669' },
  Medium: { fill: '#fef9c3', stroke: '#d97706', label: 'Medium (50-150)', dot: '#d97706' },
  High:   { fill: '#fee2e2', stroke: '#dc2626', label: 'High (>150)',   dot: '#dc2626' },
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
        stroke={selected ? '#6366f1' : dc.stroke}
        strokeWidth={selected ? '0.4%' : '0.2%'}
        opacity={0.9}
      />
      {/* Pulsing ring for sustained event zones */}
      {zone.sustained && (
        <circle
          cx={`${zone.x}%`} cy={`${zone.y}%`}
          r={(r * 1.6 + 1) + '%'}
          fill="none"
          stroke="#ef4444"
          strokeWidth="0.15%"
          strokeDasharray="1%,0.5%"
          opacity={0.7}
        >
          <animate attributeName="stroke-dashoffset" values="0;-10%" dur="2s" repeatCount="indefinite" />
        </circle>
      )}
      {/* Sustained flag */}
      {zone.sustained && (
        <text x={`${zone.x + r * 1.8}%`} y={`${zone.y - r}%`} fontSize="1.6%" textAnchor="start">{'\u26A1'}</text>
      )}
      {/* Active trigger */}
      {zone.active_trigger && (
        <text x={`${zone.x}%`} y={`${zone.y + r * 2.2}%`} fontSize="1.1%" textAnchor="middle" fill={dc.stroke}>
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
      <div className="zone-map-panel__header">
        <div>
          <h2 className="zone-map-panel__title">{'\u{1F5FA}'} Zone Map</h2>
          <p className="zone-map-panel__subtitle">
            Density bands &nbsp;&middot;&nbsp; {sustainedCount > 0 && <span className="zone-map-panel__sustained-count">{'\u26A1'} {sustainedCount} sustained events</span>}
            &nbsp;{highCount} high-density zones
          </p>
        </div>

        {/* Density filter */}
        <div className="zone-map-filter">
          {['All', 'Low', 'Medium', 'High', 'Sustained'].map(f => (
            <button
              key={f}
              className={`zone-map-filter__btn ${filter === f ? 'zone-map-filter__btn--active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="zone-map-body">
        {/* SVG schematic map */}
        <div className="zone-map-svg-wrapper">
          <svg
            viewBox="0 0 100 100"
            className="zone-map-svg"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Background */}
            <rect width="100" height="100" fill="#f0f4f8" rx="1" />

            {/* City labels */}
            {[
              { label: 'Delhi NCR', x: 22, y: 16 },
              { label: 'Bangalore', x: 22, y: 55 },
              { label: 'Mumbai',    x: 10, y: 37 },
              { label: 'Chennai',   x: 24, y: 74 },
            ].map(c => (
              <text key={c.label} x={`${c.x}%`} y={`${c.y}%`} fontSize="2%" fill="#64748b" fontWeight="bold">
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
          <div className="zone-map-legend">
            {Object.entries(DENSITY_COLORS).map(([key, val]) => (
              <div key={key} className="zone-map-legend__item">
                <span className="zone-map-legend__dot" style={{ background: val.dot }} />
                {val.label}
              </div>
            ))}
            <div className="zone-map-legend__item">
              <span className="zone-map-legend__icon">{'\u26A1'}</span> Sustained event
            </div>
          </div>
        </div>

        {/* Zone detail panel */}
        <div className="zone-detail-panel">
          {selected ? (
            <div className="zone-detail">
              <div className="zone-detail__top">
                <div>
                  <p className="zone-detail__name">{selected.name}</p>
                  <code className="zone-detail__code">{selected.id}</code>
                </div>
                <button className="zone-detail__close" onClick={() => setSelected(null)}>{'\u2715'}</button>
              </div>

              <div className="zone-detail__stats">
                <div className="zone-detail__stat">
                  <span>Density Band</span>
                  <strong style={{ color: DENSITY_COLORS[selected.density].dot }}>{selected.density}</strong>
                </div>
                <div className="zone-detail__stat">
                  <span>Active Partners</span>
                  <strong>{selected.partners}</strong>
                </div>
                <div className="zone-detail__stat">
                  <span>Loss Ratio</span>
                  <strong style={{ color: selected.lr > 85 ? '#dc3545' : selected.lr > 70 ? '#ffc107' : '#198754' }}>
                    {selected.lr}%
                  </strong>
                </div>
                <div className="zone-detail__stat">
                  <span>Active Trigger</span>
                  <strong>{selected.active_trigger || '--'}</strong>
                </div>
              </div>

              {selected.sustained && (
                <div className="zone-detail__sustained">
                  <span>{'\u26A1'}</span>
                  <div>
                    <strong>Sustained Event Active</strong>
                    <p>Payout mode switched to 70% of tier per day, no weekly cap (max 21 days). Reinsurance review flagged at day 7.</p>
                  </div>
                </div>
              )}

              <div className="zone-detail__density-info">
                <p><strong>Zone density cap:</strong></p>
                <p className="zone-detail__density-formula">
                  payout_per_partner = min(calculated_payout, zone_pool_share)<br />
                  zone_pool_share = city_weekly_reserve x zone_density_weight / partners_in_event
                </p>
              </div>
            </div>
          ) : (
            <div className="zone-detail zone-detail--empty">
              <p>Click a zone on the map to view details</p>
              <p className="zone-detail__hint">{'\u26A1'} Pulsing ring = sustained event active</p>
              <div className="zone-detail__summary">
                {['Low', 'Medium', 'High'].map(d => (
                  <div key={d} className="zone-detail__summary-row">
                    <span className="zone-map-legend__dot" style={{ background: DENSITY_COLORS[d].dot, display: 'inline-block', width: 10, height: 10, borderRadius: '50%', marginRight: 6 }} />
                    <span>{d}</span>
                    <span>{zones.filter(z => z.density === d).length} zones</span>
                    <span>{zones.filter(z => z.density === d).reduce((a, z) => a + z.partners, 0)} partners</span>
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
