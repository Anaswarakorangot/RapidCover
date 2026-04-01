export default function ExclusionsCard() {
  const exclusions = [
    { icon: '⚔️', label: 'War & armed conflict', detail: 'Permanently excluded', attempted: 0 },
    { icon: '🦠', label: 'Pandemic / epidemic declarations', detail: 'Government-declared only', attempted: 0 },
    { icon: '☢️', label: 'Nuclear / radioactive events', detail: 'Permanently excluded', attempted: 0 },
    { icon: '⏱️', label: 'Events under 45 minutes', detail: 'De minimis threshold', attempted: 3 },
    { icon: '⚙️', label: 'Platform operational decisions', detail: 'Scheduled maintenance, algorithm changes', attempted: 1 },
    { icon: '🚷', label: 'Self-inflicted loss', detail: 'Voluntary offline by worker', attempted: 0 },
    { icon: '🏥', label: 'Health / accident / life', detail: 'Strictly out of scope', attempted: 0 },
    { icon: '🚗', label: 'Vehicle damage', detail: 'Not covered under parametric model', attempted: 0 },
  ];

  return (
    <div className="admin-section" style={{ animationDelay: '0.7s' }}>
      <div className="admin-section-label">COVERAGE EXCLUSIONS — ACTIVE POLICY</div>
      <div className="exclusions-irdai-badge">IRDAI-aligned parametric exclusions</div>

      <div className="exclusions-grid">
        {exclusions.map(e => (
          <div key={e.label} className="exclusion-item">
            <span className="exclusion-icon">{e.icon}</span>
            <div className="exclusion-text">
              <span className="exclusion-label">{e.label}</span>
              <span className="exclusion-detail">{e.detail}</span>
            </div>
            <span className={`exclusion-attempted ${e.attempted > 0 ? 'exclusion-attempted--active' : ''}`}>
              {e.attempted} blocked
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
