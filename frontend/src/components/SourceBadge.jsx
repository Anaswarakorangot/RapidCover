/**
 * SourceBadge.jsx  –  Reusable trigger-source / disruption-type badge
 *
 * B2 shared component. Used in Dashboard, Claims, ProofCard, and admin panels.
 *
 * Props:
 *   type      {string}  'rain' | 'heat' | 'aqi' | 'shutdown' | 'closure'
 *   severity  {number?} 1–5  (optional – renders severity chip when provided)
 *   size      {'sm'|'md'|'lg'} default 'md'
 *   showLabel {boolean} default true
 */

const TYPE_MAP = {
  rain:     { icon: '🌧️', label: 'Heavy Rain',     color: '#eff6ff', border: '#bfdbfe', text: '#1e40af' },
  heat:     { icon: '🌡️', label: 'Extreme Heat',   color: '#fef2f2', border: '#fecaca', text: '#991b1b' },
  aqi:      { icon: '💨', label: 'Dangerous AQI',  color: '#fffbeb', border: '#fde68a', text: '#92400e' },
  shutdown: { icon: '🚫', label: 'Civic Shutdown',  color: '#faf5ff', border: '#e9d5ff', text: '#6b21a8' },
  closure:  { icon: '🏪', label: 'Store Closure',   color: '#f9fafb', border: '#e5e7eb', text: '#374151' },
};

const FALLBACK = { icon: '⚠️', label: 'Event', color: '#f9fafb', border: '#e5e7eb', text: '#374151' };

const SIZE_MAP = {
  sm: { fontSize: 11, padding: '2px 8px',  iconSize: 14, gap: 4 },
  md: { fontSize: 12, padding: '4px 10px', iconSize: 16, gap: 5 },
  lg: { fontSize: 13, padding: '5px 13px', iconSize: 20, gap: 6 },
};

const SEVERITY_COLORS = {
  1: { bg: '#f0fdf4', text: '#166534' },
  2: { bg: '#dbeafe', text: '#1e40af' },
  3: { bg: '#fef9c3', text: '#854d0e' },
  4: { bg: '#fee2e2', text: '#991b1b' },
  5: { bg: '#fdf2f8', text: '#9d174d' },
};

export default function SourceBadge({ type, severity, size = 'md', showLabel = true }) {
  const meta  = TYPE_MAP[type?.toLowerCase()] || FALLBACK;
  const sizes = SIZE_MAP[size] || SIZE_MAP.md;
  const sevColor = severity ? (SEVERITY_COLORS[severity] || SEVERITY_COLORS[3]) : null;

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      {/* Main type badge */}
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: sizes.gap,
          background: meta.color,
          border: `1.5px solid ${meta.border}`,
          color: meta.text,
          fontSize: sizes.fontSize,
          fontWeight: 700,
          padding: sizes.padding,
          borderRadius: 20,
          fontFamily: "'DM Sans', sans-serif",
          whiteSpace: 'nowrap',
        }}
        title={`${meta.label}${severity ? ` · Severity ${severity}/5` : ''}`}
      >
        <span style={{ fontSize: sizes.iconSize, lineHeight: 1 }}>{meta.icon}</span>
        {showLabel && meta.label}
      </span>

      {/* Optional severity chip */}
      {severity != null && sevColor && (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            background: sevColor.bg,
            color: sevColor.text,
            fontSize: sizes.fontSize - 1,
            fontWeight: 700,
            padding: '2px 7px',
            borderRadius: 20,
            fontFamily: "'DM Sans', sans-serif",
          }}
        >
          S{severity}
        </span>
      )}
    </span>
  );
}
