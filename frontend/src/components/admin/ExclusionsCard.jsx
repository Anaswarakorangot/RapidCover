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
    <div className="admin-section" style={{ background: 'var(--white)', border: '1.5px solid var(--border)', borderRadius: '24px', padding: '1.5rem', marginTop: '1.5rem' }}>
      <div className="admin-section-label" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '0.8rem', color: 'var(--text-light)', textTransform: 'uppercase', marginBottom: '1rem', letterSpacing: '0.05em' }}>
        Coverage Exclusions — Active Policy
      </div>
      
      <div className="exclusions-irdai-badge" style={{ display: 'inline-block', background: 'var(--gray-bg)', padding: '0.4rem 0.8rem', borderRadius: '10px', fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-mid)', marginBottom: '1.5rem' }}>
        IRDAI-aligned parametric exclusions
      </div>

      <div className="exclusions-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
        {exclusions.map(e => (
          <div 
            key={e.label} 
            className="exclusion-item" 
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '1rem', 
              padding: '1rem', 
              background: 'var(--gray-bg)', 
              borderRadius: '16px',
              border: '1px solid transparent',
              transition: 'all 0.2s'
            }}
          >
            <span className="exclusion-icon" style={{ fontSize: '1.5rem' }}>{e.icon}</span>
            <div className="exclusion-text" style={{ flex: 1 }}>
              <span className="exclusion-label" style={{ display: 'block', fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dark)' }}>{e.label}</span>
              <span className="exclusion-detail" style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-light)', marginTop: '0.1rem' }}>{e.detail}</span>
            </div>
            {e.attempted > 0 && (
              <span 
                className="exclusion-attempted--active" 
                style={{ fontSize: '0.6rem', fontWeight: 900, background: 'var(--error)', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '6px' }}
              >
                {e.attempted} blocked
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
