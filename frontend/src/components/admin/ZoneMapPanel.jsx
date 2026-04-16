/**
 * ZoneMapPanel.jsx  –  Enhanced Rider-Aware Leaflet Map
 *
 * Color scheme:
 *   🔵 Blue pulsing dot  = Rider's current GPS location
 *   🟢 Green fill        = Rider's own registered zone
 *   🟡 Amber/Orange fill = Nearby zones (within ~5 km radius)
 *   ⚫ Dim grey fill     = All other operational zones
 *
 * Trigger/weather icons are rendered as custom DivIcon markers
 * placed at each zone's centroid when the zone has active triggers.
 */

import { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polygon, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import api from '../../services/api';

// ── Fix default Leaflet icons in bundled environments ─────────────────────────
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl:       'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl:     'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// ── Trigger → icon/label map ──────────────────────────────────────────────────
const TRIGGER_ICONS = {
  rain:     { emoji: '🌧️', label: 'Heavy Rain',    bg: '#dbeafe', border: '#3b82f6' },
  heat:     { emoji: '🌡️', label: 'Extreme Heat',  bg: '#fee2e2', border: '#ef4444' },
  aqi:      { emoji: '💨', label: 'Dangerous AQI', bg: '#fef3c7', border: '#f59e0b' },
  shutdown: { emoji: '🚫', label: 'Civic Shutdown', bg: '#ede9fe', border: '#8b5cf6' },
  closure:  { emoji: '🏪', label: 'Store Closure',  bg: '#f3f4f6', border: '#6b7280' },
  flood:    { emoji: '🌊', label: 'Flooding',        bg: '#dbeafe', border: '#2563eb' },
  storm:    { emoji: '⛈️', label: 'Thunderstorm',   bg: '#e0e7ff', border: '#4f46e5' },
};

// ── Zone colour palette ───────────────────────────────────────────────────────
const ZONE_COLORS = {
  rider:  { fill: '#22c55e', stroke: '#16a34a', opacity: 0.30 },   // own zone – green
  nearby: { fill: '#f59e0b', stroke: '#d97706', opacity: 0.28 },   // adjacent  – amber
  other:  { fill: '#94a3b8', stroke: '#64748b', opacity: 0.12 },   // rest      – grey
};

// ── Haversine distance (km) ───────────────────────────────────────────────────
function haversineDist([lat1, lng1], [lat2, lng2]) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ── Centroid of a polygon ─────────────────────────────────────────────────────
function centroid(coords) {
  if (!coords?.length) return null;
  const lat = coords.reduce((s, c) => s + c[0], 0) / coords.length;
  const lng = coords.reduce((s, c) => s + c[1], 0) / coords.length;
  return [lat, lng];
}

// ── MapBoundsUpdater ──────────────────────────────────────────────────────────
function MapBoundsUpdater({ mapData, riderPos, demoMode }) {
  const map = useMap();
  useEffect(() => {
    if (!mapData) return;
    const bounds = L.latLngBounds([]);
    if (riderPos) bounds.extend(riderPos);
    // Only fit polygon centroids (ignore markers in demo to avoid zooming out)
    mapData.polygons?.forEach(p =>
      p.coordinates?.forEach(coord => bounds.extend(coord))
    );
    if (!demoMode) {
      // In live mode also include dark store markers
      mapData.markers?.forEach(m => bounds.extend([m.lat, m.lng]));
    }
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    } else if (mapData.center) {
      map.setView(mapData.center, mapData.zoom || 13);
    }
  }, [mapData, riderPos, map, demoMode]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

// ── Trigger icon marker ───────────────────────────────────────────────────────
function triggerDivIcon(triggersForZone) {
  // Stack first 3 icons neatly
  const icons = triggersForZone.slice(0, 3);
  const html = icons
    .map(t => {
      const info = TRIGGER_ICONS[t.trigger_type] || TRIGGER_ICONS.rain;
      return `
        <div style="
          background:${info.bg};
          border:2px solid ${info.border};
          border-radius:50%;
          width:30px;height:30px;
          display:flex;align-items:center;justify-content:center;
          font-size:15px;
          box-shadow:0 2px 8px rgba(0,0,0,0.18);
          margin:2px auto;
        ">${info.emoji}</div>`;
    })
    .join('');
  return L.divIcon({
    html: `<div style="display:flex;flex-direction:column;align-items:center;">${html}</div>`,
    className: 'trigger-icon-marker',
    iconSize:  [34, icons.length * 34],
    iconAnchor:[17, (icons.length * 34) / 2],
  });
}

// ── Rider dot icon ────────────────────────────────────────────────────────────
const riderIcon = L.divIcon({
  html: `
    <div style="position:relative;width:22px;height:22px;">
      <div style="
        position:absolute;inset:0;
        background:rgba(59,130,246,0.25);
        border-radius:50%;
        animation:riderPulse 1.8s ease-out infinite;
      "></div>
      <div style="
        position:absolute;top:50%;left:50%;
        transform:translate(-50%,-50%);
        background:#3b82f6;
        width:12px;height:12px;
        border:2.5px solid white;
        border-radius:50%;
        box-shadow:0 0 8px rgba(59,130,246,0.6);
      "></div>
    </div>`,
  className: 'rider-location-marker',
  iconSize:   [22, 22],
  iconAnchor: [11, 11],
});

// ── Inline CSS for animations (injected once) ─────────────────────────────────
const MAP_STYLES = `
  @keyframes riderPulse {
    0%   { transform: scale(0.6); opacity: 0.8; }
    100% { transform: scale(2.2); opacity: 0; }
  }
  .trigger-icon-marker { background: transparent !important; border: none !important; }
  .rider-location-marker { background: transparent !important; border: none !important; }
  .zone-map-panel { font-family: 'DM Sans', sans-serif; }
  .map-wrapper {
    height: 460px;
    border-radius: 20px;
    overflow: hidden;
    border: 1.5px solid var(--border, #e2ece2);
    position: relative;
  }

  .map-overlay-info {
    position: absolute;
    top: 16px; right: 16px;
    z-index: 1000;
    background: rgba(255,255,255,0.96);
    backdrop-filter: blur(8px);
    border-radius: 16px;
    padding: 12px 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.14);
    border: 1.5px solid #e5e7eb;
    max-width: 220px;
    font-size: 12px;
  }
`;

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Props:
 *   riderZoneId   {number|null} – The zone the rider is assigned to (from user.zone_id)
 *   activeTriggers {Array}      – Active trigger objects [{trigger_type, zone_id, ...}]
 *   onZoneClick   {Function}    – Callback when a zone polygon is clicked
 */
export default function ZoneMapPanel({ riderZoneId, activeTriggers = [], onZoneClick, demoMode }) {
  const [mapData,      setMapData]      = useState(null);
  const [riderPos,     setRiderPos]     = useState(null);
  const [selectedZone, setSelectedZone] = useState(null);
  const [loading,      setLoading]      = useState(true);
  const [nearbyRadius] = useState(10); // km

  // ── Fetch zone map data ──────────────────────────────────────────────────
  const fetchMap = async (cityFilter = null) => {
    try {
      const data = await api.getZonesMap(cityFilter);
      setMapData(data);
    } catch {
      // Map data unavailable
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // In demo mode, only load Hyderabad zones so the map doesn't zoom across India
    const city = demoMode ? 'Hyderabad' : null;
    fetchMap(city);
    const interval = setInterval(() => fetchMap(demoMode ? 'Hyderabad' : null), 30_000);

    // Request geolocation if not in demo mode
    if (!demoMode && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => setRiderPos([pos.coords.latitude, pos.coords.longitude]),
        err => console.warn('Geolocation unavailable:', err),
        { enableHighAccuracy: true }
      );
    }

    return () => clearInterval(interval);
  }, [demoMode]);

  // Handle demo mode toggling
  useEffect(() => {
    if (demoMode && mapData?.polygons?.length > 0) {
      // Place rider between HYD-001 (Chanda Nagar: 17.4923, 78.3308)
      // and HYD-002 (Kukatpally: 17.4816, 78.3940)
      // At this midpoint, both zones are within 5-6 km → one green, one orange
      setRiderPos([17.4870, 78.3620]);
    } else if (!demoMode) {
      setRiderPos(null);
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          pos => setRiderPos([pos.coords.latitude, pos.coords.longitude]),
          err => console.warn('Geolocation unavailable:', err),
          { enableHighAccuracy: true }
        );
      }
    }
  }, [demoMode, mapData]);

  // ── Derived: group zones by relationship to rider ───────────────────────
  const { zoneClassMap, triggersByZone, polygonsWithRole } = useMemo(() => {
    if (!mapData?.polygons) return { zoneClassMap: {}, triggersByZone: {}, polygonsWithRole: [] };

    // In demo mode, if we don't have a rider zone, pick the zone nearest to demo rider pos
    let effectiveRiderZoneId = riderZoneId;
    if (demoMode && !riderZoneId && mapData.polygons.length > 0) {
      // Pick HYD-001 (first Hyderabad zone) as the demo "your zone"
      effectiveRiderZoneId = mapData.polygons[0].zone_id;
    }

    // Build trigger index: zone_id → [triggers]
    const trigByZone = {};
    activeTriggers.forEach(t => {
      const zid = t.zone_id ?? t.zoneId;
      if (zid != null) {
        if (!trigByZone[zid]) trigByZone[zid] = [];
        trigByZone[zid].push(t);
      }
    });

    // Classify each polygon
    const clsMap = {};
    const withRole = mapData.polygons.map(poly => {
      const zid = poly.zone_id;
      let role = 'other';

      if (effectiveRiderZoneId && zid === effectiveRiderZoneId) {
        role = 'rider';
      } else if (riderPos) {
        const c = centroid(poly.coordinates);
        if (c && haversineDist(riderPos, c) <= nearbyRadius) {
          role = 'nearby';
        }
      }

      clsMap[zid] = role;
      return { ...poly, role };
    });

    return { zoneClassMap: clsMap, triggersByZone: trigByZone, polygonsWithRole: withRole };
  }, [mapData, riderZoneId, riderPos, activeTriggers, nearbyRadius, demoMode]);

  // In demo mode inject fake triggers to show weather icons
  const demoDemoTriggers = useMemo(() => {
    if (!demoMode || !mapData?.polygons?.length) return triggersByZone;
    const result = { ...triggersByZone };
    // Add a rain trigger to the 2nd polygon (nearby zone) if no real triggers
    const secondZoneId = polygonsWithRole.find(p => p.role === 'nearby')?.zone_id;
    if (secondZoneId && !result[secondZoneId]) {
      result[secondZoneId] = [{ trigger_type: 'rain', severity: 'high', zone_id: secondZoneId }];
    }
    return result;
  }, [demoMode, triggersByZone, mapData, polygonsWithRole]);

  // ── Zone click handler ───────────────────────────────────────────────────
  const handleZoneSelect = (poly) => {
    if (onZoneClick) onZoneClick(poly.zone_id);
    setSelectedZone({
      id:   poly.zone_id,
      name: poly.zone_name || `Zone ${poly.zone_id}`,
      role: poly.role,
      suspended: poly.is_suspended,
    });
  };

  if (loading && !mapData) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#8a9e8a', fontSize: 13 }}>
        <div style={{
          width: 32, height: 32, margin: '0 auto 12px',
          border: '3px solid #e8f7ed', borderTopColor: '#3DB85C',
          borderRadius: '50%', animation: 'spin 0.8s linear infinite',
        }} />
        Loading map…
      </div>
    );
  }

  return (
    <section className="zone-map-panel">
      <style>{MAP_STYLES}</style>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, padding: '0 2px' }}>
        <div>
          <h2 style={{ fontFamily: 'Nunito, sans-serif', fontWeight: 900, fontSize: '1.2rem', color: 'var(--text-dark, #1a2e1a)', margin: 0 }}>
            📍 Live Coverage Map
          </h2>
          <p style={{ fontSize: 12, color: 'var(--text-light, #8a9e8a)', marginTop: 2 }}>
            Your zone · nearby zones · active triggers
          </p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
          {demoMode && (
            <span style={{
              fontSize: 10, fontWeight: 700, padding: '3px 10px', borderRadius: 12,
              background: '#fef3c7', color: '#92400e', border: '1px solid #fde68a',
            }}>🧪 DEMO MODE — Hyderabad</span>
          )}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 20,
            background: demoMode ? '#fef3c7' : '#e8f7ed',
            color: demoMode ? '#92400e' : '#2a9e47',
          }}>
            <span style={{
              width: 6, height: 6,
              background: demoMode ? '#f59e0b' : '#3DB85C',
              borderRadius: '50%', animation: 'riderPulse 1.8s ease-out infinite',
            }} />
            {demoMode ? 'SIMULATED' : 'LIVE'}
          </div>
        </div>
      </div>

      <div className="map-wrapper">
        <MapContainer
          center={mapData?.center || [17.3850, 78.4867]}
          zoom={mapData?.zoom || 11}
          scrollWheelZoom={false}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MapBoundsUpdater mapData={mapData} riderPos={riderPos} demoMode={demoMode} />

          {/* ── Zone Polygons ─────────────────────────────────────────────── */}
          {polygonsWithRole.map((poly, i) => {
            const scheme = ZONE_COLORS[poly.role] || ZONE_COLORS.other;
            const hasTrigger = !!demoDemoTriggers[poly.zone_id];
            return (
              <Polygon
                key={`poly-${i}`}
                positions={poly.coordinates}
                pathOptions={{
                  fillColor:    scheme.fill,
                  fillOpacity:  poly.is_suspended ? 0.06 : scheme.opacity,
                  color:        hasTrigger ? '#ef4444' : scheme.stroke,
                  weight:       poly.role === 'rider' ? 3 : (hasTrigger ? 2.5 : 1.5),
                  dashArray:    poly.is_suspended ? '6 4' : '',
                  opacity:      poly.is_suspended ? 0.5 : 1,
                }}
                eventHandlers={{ click: () => handleZoneSelect(poly) }}
              >
                <Popup>
                  <div style={{ padding: 4, minWidth: 140 }}>
                    <p style={{ fontWeight: 800, fontSize: 13, marginBottom: 4 }}>
                      {poly.zone_name || `Zone ${poly.zone_id}`}
                    </p>
                    <p style={{ fontSize: 11, color: '#6b7280', marginBottom: 6 }}>
                      {poly.role === 'rider'
                        ? '🟢 Your Zone'
                        : poly.role === 'nearby'
                        ? '🟡 Nearby Zone'
                        : '⚫ Other Zone'}
                    </p>
                    {poly.is_suspended && (
                      <p style={{ fontSize: 11, color: '#dc2626', fontWeight: 700 }}>⚠️ Suspended</p>
                    )}
                    {demoDemoTriggers[poly.zone_id]?.map((t, ti) => {
                      const info = TRIGGER_ICONS[t.trigger_type] || {};
                      return (
                        <p key={ti} style={{ fontSize: 11, color: '#b45309', marginTop: 2 }}>
                          {info.emoji || '⚠️'} {info.label || t.trigger_type}
                        </p>
                      );
                    })}
                  </div>
                </Popup>
              </Polygon>
            );
          })}

          {/* ── Trigger / Weather Icon Markers ─────────────────────────────── */}
          {polygonsWithRole.map((poly, i) => {
            const triggers = demoDemoTriggers[poly.zone_id];
            if (!triggers?.length) return null;
            const c = centroid(poly.coordinates);
            if (!c) return null;
            return (
              <Marker
                key={`trig-${i}`}
                position={c}
                icon={triggerDivIcon(triggers)}
                zIndexOffset={500}
              >
                <Popup>
                  <div style={{ padding: 4, minWidth: 160 }}>
                    <p style={{ fontWeight: 800, fontSize: 12, marginBottom: 6, color: '#dc2626' }}>
                      ⚠️ Active Alert{triggers.length > 1 ? 's' : ''} — {poly.zone_name}
                    </p>
                    {triggers.map((t, ti) => {
                      const info = TRIGGER_ICONS[t.trigger_type] || {};
                      return (
                        <div key={ti} style={{
                          display: 'flex', alignItems: 'center', gap: 6,
                          padding: '4px 0', fontSize: 12, borderBottom: ti < triggers.length - 1 ? '1px solid #f3f4f6' : 'none',
                        }}>
                          <span>{info.emoji || '⚠️'}</span>
                          <span style={{ color: '#374151' }}>{info.label || t.trigger_type}</span>
                          {t.severity && (
                            <span style={{
                              marginLeft: 'auto', fontSize: 10, fontWeight: 700,
                              padding: '1px 6px', borderRadius: 8,
                              background: t.severity === 'critical' ? '#fee2e2' : '#fef3c7',
                              color: t.severity === 'critical' ? '#dc2626' : '#b45309',
                            }}>
                              {t.severity.toUpperCase()}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* ── Dark Store / Depot Markers ─────────────────────────────────── */}
          {mapData?.markers?.map((marker, i) => (
            <Marker key={`store-${i}`} position={[marker.lat, marker.lng]}>
              <Popup>
                <div style={{ padding: 4 }}>
                  <p style={{ fontWeight: 800, fontSize: 13, marginBottom: 2 }}>{marker.label}</p>
                  <p style={{ fontSize: 11, color: '#6b7280' }}>Dark Store / Depot</p>
                </div>
              </Popup>
            </Marker>
          ))}

          {/* ── Rider GPS Dot ─────────────────────────────────────────────── */}
          {riderPos && (
            <Marker position={riderPos} icon={riderIcon} zIndexOffset={1000}>
              <Popup>
                <div style={{ padding: 4 }}>
                  <p style={{ fontWeight: 800, fontSize: 13 }}>📍 You are here</p>
                  <p style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>
                    {riderPos[0].toFixed(5)}, {riderPos[1].toFixed(5)}
                  </p>
                </div>
              </Popup>
            </Marker>
          )}
        </MapContainer>



        {/* ── Selected zone info panel ───────────────────────────────────── */}
        {selectedZone && (
          <div className="map-overlay-info">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <p style={{ fontWeight: 800, fontSize: 14, margin: 0 }}>{selectedZone.name}</p>
                <p style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>
                  {selectedZone.role === 'rider'
                    ? '🟢 Your Zone'
                    : selectedZone.role === 'nearby'
                    ? '🟡 Nearby Zone'
                    : '⚫ Other Zone'}
                </p>
              </div>
              <button
                onClick={() => setSelectedZone(null)}
                style={{
                  background: '#f3f4f6', border: 'none', borderRadius: '50%',
                  width: 22, height: 22, cursor: 'pointer',
                  fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >×</button>
            </div>

            {selectedZone.suspended && (
              <div style={{ marginTop: 8, background: '#fef2f2', borderRadius: 8, padding: '6px 10px', fontSize: 11, color: '#dc2626', fontWeight: 700 }}>
                ⚠️ Zone Suspended
              </div>
            )}

            {demoDemoTriggers[selectedZone.id]?.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <p style={{ fontSize: 10, color: '#6b7280', fontWeight: 700, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Active Triggers
                </p>
                {demoDemoTriggers[selectedZone.id].map((t, ti) => {
                  const info = TRIGGER_ICONS[t.trigger_type] || {};
                  return (
                    <div key={ti} style={{
                      display: 'flex', alignItems: 'center', gap: 6,
                      padding: '5px 0', fontSize: 12,
                      borderBottom: ti < demoDemoTriggers[selectedZone.id].length - 1 ? '1px solid #f3f4f6' : 'none',
                    }}>
                      <span>{info.emoji || '⚠️'}</span>
                      <span style={{ flex: 1, color: '#374151' }}>{info.label || t.trigger_type}</span>
                      {t.severity && (
                        <span style={{
                          fontSize: 9, fontWeight: 700, padding: '1px 5px',
                          borderRadius: 6,
                          background: t.severity === 'critical' ? '#fee2e2' : '#fef3c7',
                          color: t.severity === 'critical' ? '#dc2626' : '#b45309',
                        }}>
                          {t.severity.toUpperCase()}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
