export default function ExclusionsCard() {
  const exclusions = [
    { icon: '⚔️', label: 'War & armed conflict', detail: 'Permanently excluded' },
    { icon: '🦠', label: 'Pandemic / epidemic declarations', detail: 'Government-declared only' },
    { icon: '☢️', label: 'Nuclear / radioactive events', detail: 'Permanently excluded' },
    { icon: '⏱️', label: 'Events under 45 minutes', detail: 'De minimis threshold' },
    { icon: '⚙️', label: 'Platform operational decisions', detail: 'Scheduled maintenance, algorithm changes' },
    { icon: '🚷', label: 'Self-inflicted loss', detail: 'Voluntary offline by worker' },
    { icon: '🏥', label: 'Health / accident / life', detail: 'Strictly out of scope' },
    { icon: '🚗', label: 'Vehicle damage', detail: 'Not covered under parametric model' },
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
          </div>
        ))}
      </div>
    </div>
  );
}
