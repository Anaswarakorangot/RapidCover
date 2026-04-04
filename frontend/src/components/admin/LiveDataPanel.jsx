// frontend/src/components/admin/LiveDataPanel.jsx
// Shows live API data (weather, AQI, platform status) with refresh button

import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const SOURCE_COLORS = {
  live: '#22c55e',
  mock: '#f59e0b',
  unknown: '#94a3b8',
};

export default function LiveDataPanel() {
  const [data, setData] = useState(null);
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState('');
  const [loading, setLoading] = useState(false);
  const [lastFetch, setLastFetch] = useState(null);

  useEffect(() => {
    fetchZones();
  }, []);

  useEffect(() => {
    if (selectedZone) {
      fetchLiveData();
    }
  }, [selectedZone]);

  async function fetchZones() {
    try {
      const res = await fetch(`${API_BASE}/zones`);
      if (res.ok) {
        const list = await res.json();
        setZones(list);
        if (list.length > 0) {
          setSelectedZone(list[0].code);
        }
      }
    } catch (err) {
      console.error('Failed to fetch zones:', err);
    }
  }

  async function fetchLiveData() {
    if (!selectedZone) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/panel/live-data?zone_code=${selectedZone}`);
      if (res.ok) {
        const result = await res.json();
        setData(result);
        setLastFetch(new Date());
      }
    } catch (err) {
      console.error('Failed to fetch live data:', err);
    }
    setLoading(false);
  }

  function SourceBadge({ source }) {
    return (
      <span style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '12px',
        fontSize: '0.7rem',
        fontWeight: 700,
        textTransform: 'uppercase',
        background: `${SOURCE_COLORS[source] || SOURCE_COLORS.unknown}20`,
        color: SOURCE_COLORS[source] || SOURCE_COLORS.unknown,
      }}>
        {source}
      </span>
    );
  }

  function DataCard({ title, icon, source, children }) {
    return (
      <div style={{
        background: 'var(--white)',
        borderRadius: '16px',
        border: '1.5px solid var(--border)',
        padding: '1rem',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>{icon}</span>
            <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>{title}</span>
          </div>
          <SourceBadge source={source} />
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
          {value}{unit && <span style={{ color: 'var(--text-light)', fontWeight: 400 }}> {unit}</span>}
        </span>
      </div>
    );
  }

  return (
    <section style={{ padding: '0' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)', marginBottom: '0.25rem' }}>
          📡 Live API Data
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-light)' }}>
          Real-time data from external APIs (OpenWeatherMap, WAQI, etc.)
        </p>
      </div>

      {/* Controls */}
      <div style={{
        display: 'flex',
        gap: '1rem',
        alignItems: 'center',
        marginBottom: '1.5rem',
        padding: '1rem',
        background: 'var(--white)',
        borderRadius: '14px',
        border: '1.5px solid var(--border)',
      }}>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-light)', display: 'block', marginBottom: '0.25rem' }}>
            SELECT ZONE
          </label>
          <select
            value={selectedZone}
            onChange={(e) => setSelectedZone(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem',
              borderRadius: '8px',
              border: '1.5px solid var(--border)',
              fontSize: '0.9rem',
              fontWeight: 600,
            }}
          >
            {zones.map(z => (
              <option key={z.code} value={z.code}>{z.code} — {z.name}</option>
            ))}
          </select>
        </div>
        <button
          onClick={fetchLiveData}
          disabled={loading}
          style={{
            padding: '0.75rem 1.5rem',
            borderRadius: '10px',
            background: loading ? 'var(--text-light)' : 'var(--primary)',
            color: 'white',
            border: 'none',
            fontWeight: 800,
            fontSize: '0.9rem',
            cursor: loading ? 'wait' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          {loading ? (
            <>
              <span style={{ width: 14, height: 14, border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
              Fetching...
            </>
          ) : (
            <>🔄 Refresh</>
          )}
        </button>
      </div>

      {/* Last fetch time */}
      {lastFetch && (
        <p style={{ fontSize: '0.75rem', color: 'var(--text-light)', marginBottom: '1rem' }}>
          Last fetched: {lastFetch.toLocaleTimeString()}
        </p>
      )}

      {/* Data cards */}
      {data && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
          {/* Weather */}
          <DataCard title="Weather" icon="🌤️" source={data.weather?.source}>
            <Metric label="Temperature" value={data.weather?.temp_celsius} unit="°C" />
            <Metric label="Rainfall" value={data.weather?.rainfall_mm_hr} unit="mm/hr" />
            <Metric label="Humidity" value={data.weather?.humidity} unit="%" />
          </DataCard>

          {/* AQI */}
          <DataCard title="Air Quality" icon="💨" source={data.aqi?.source}>
            <Metric label="AQI Index" value={data.aqi?.aqi} />
            <Metric label="PM2.5" value={data.aqi?.pm25} unit="μg/m³" />
            <Metric label="PM10" value={data.aqi?.pm10} unit="μg/m³" />
            <Metric label="Category" value={data.aqi?.category} />
          </DataCard>

          {/* Platform Status */}
          <DataCard title="Platform Status" icon="🏪" source={data.platform?.source}>
            <Metric
              label="Store Status"
              value={data.platform?.is_open ? '✅ Open' : '❌ Closed'}
            />
            {data.platform?.closure_reason && (
              <Metric label="Reason" value={data.platform.closure_reason} />
            )}
          </DataCard>

          {/* Shutdown Status */}
          <DataCard title="Civic Status" icon="🚨" source={data.shutdown?.source}>
            <Metric
              label="Shutdown"
              value={data.shutdown?.is_active ? '⚠️ Active' : '✅ Normal'}
            />
            {data.shutdown?.reason && (
              <Metric label="Reason" value={data.shutdown.reason} />
            )}
          </DataCard>
        </div>
      )}

      {/* Source Health */}
      {data?.source_health && (
        <div style={{ marginTop: '1.5rem' }}>
          <h3 style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)', marginBottom: '0.75rem' }}>
            API Source Health
          </h3>
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.5rem',
          }}>
            {Object.entries(data.source_health).map(([name, info]) => (
              <div
                key={name}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 0.75rem',
                  background: 'var(--white)',
                  borderRadius: '10px',
                  border: '1.5px solid var(--border)',
                }}
              >
                <span style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: SOURCE_COLORS[info.status] || SOURCE_COLORS.unknown,
                }} />
                <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{name}</span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-light)' }}>
                  {info.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Zone info */}
      {data?.zone && (
        <div style={{
          marginTop: '1rem',
          padding: '0.75rem 1rem',
          background: 'var(--bg-light)',
          borderRadius: '10px',
          fontSize: '0.75rem',
          color: 'var(--text-light)',
        }}>
          Zone: <strong>{data.zone.name}</strong> ({data.zone.city}) ·
          Lat: {data.zone.lat?.toFixed(4)} · Lng: {data.zone.lng?.toFixed(4)}
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
