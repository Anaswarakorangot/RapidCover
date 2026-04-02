// frontend/src/components/admin/MLStatusPanel.jsx
// Shows Zone Risk Scorer / Premium Engine / Fraud Detector as "active"
// with their model type labels (XGBoost / Gradient Boosted / Isolation Forest)

export default function MLStatusPanel() {
  const models = [
    {
      name: 'Zone Risk Scorer',
      algo: 'XGBoost',
      status: 'active',
      desc: 'Classifies zone disruption risk using historical trigger frequency, road density (RIQI), and seasonal indices.',
      features: ['trigger_frequency', 'riqi_score', 'zone_density', 'seasonal_index'],
      version: 'v2.1.0',
      icon: '\u{1F5FA}\uFE0F',
    },
    {
      name: 'Premium Engine',
      algo: 'Gradient Boosted',
      status: 'active',
      desc: 'Calculates personalised weekly premium using 7-factor formula -- city peril, zone risk, seasonal index, activity tier, RIQI, and loyalty discount.',
      features: ['trigger_probability', 'city_peril_multiplier', 'zone_risk_score', 'activity_tier_factor', 'riqi_adjustment', 'seasonal_index', 'loyalty_discount'],
      version: 'v1.8.3',
      icon: '\u{1F4B0}',
    },
    {
      name: 'Fraud Detector',
      algo: 'Isolation Forest',
      status: 'active',
      desc: '7-factor weighted fraud scoring model. Detects GPS spoofing, collusion rings, and GPS centroid drift.',
      features: ['gps_coherence (w=0.25)', 'run_count_check (w=0.25)', 'zone_polygon_match (w=0.15)', 'claim_frequency (w=0.15)', 'device_fingerprint (w=0.10)', 'traffic_cross_check (w=0.05)', 'centroid_drift (w=0.05)'],
      version: 'v3.0.1',
      icon: '\u{1F50D}',
    },
  ];

  const thresholds = [
    { label: 'Auto-approve', range: '< 0.50', color: '#198754' },
    { label: 'Enhanced check', range: '0.50 - 0.75', color: '#ffc107' },
    { label: 'Manual queue', range: '0.75 - 0.90', color: '#fd7e14' },
    { label: 'Auto-reject', range: '> 0.90', color: '#dc3545' },
  ];

  return (
    <section className="ml-panel">
      <div className="ml-panel__header" style={{ marginBottom: '2rem' }}>
        <h2 className="ml-panel__title" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)' }}>{'\u{1F916}'} ML Model Status</h2>
        <p className="ml-panel__subtitle" style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.4rem' }}>
          All models active &nbsp;&middot;&nbsp; 7-factor weighted scoring &nbsp;&middot;&nbsp; Rules-based fallback hot-standby
        </p>
      </div>

      <div className="ml-panel__grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' }}>
        {models.map(m => (
          <div 
            key={m.name} 
            className="ml-card" 
            style={{ 
              background: 'var(--white)', 
              border: '1.5px solid var(--border)', 
              borderRadius: '24px', 
              padding: '1.5rem',
              transition: 'all 0.2s',
              position: 'relative'
            }}
          >
            <div className="ml-card__top" style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <span className="ml-card__icon" style={{ fontSize: '1.75rem', background: 'var(--gray-bg)', padding: '0.75rem', borderRadius: '16px' }}>{m.icon}</span>
              <div className="ml-card__title-block" style={{ flex: 1 }}>
                <p className="ml-card__name" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.15rem', color: 'var(--text-dark)' }}>{m.name}</p>
                <div className="ml-card__badges" style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                  <span className="ml-card__algo" style={{ fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-mid)' }}>{m.algo}</span>
                  <span className="ml-card__status" style={{ fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--green-primary)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <span className="ml-card__dot" style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green-primary)' }} /> Active
                  </span>
                </div>
              </div>
              <span className="ml-card__version" style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-light)', background: 'var(--gray-bg)', padding: '0.2rem 0.5rem', borderRadius: '6px' }}>{m.version}</span>
            </div>

            <p className="ml-card__desc" style={{ fontSize: '0.85rem', color: 'var(--text-mid)', lineHeight: 1.5, marginBottom: '1.5rem' }}>{m.desc}</p>

            <div className="ml-card__features" style={{ borderTop: '1px solid var(--border)', paddingTop: '1.25rem' }}>
              <p className="ml-card__features-label" style={{ fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)', marginBottom: '0.75rem' }}>Input features</p>
              <div className="ml-card__feature-list" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                {m.features.map(f => (
                  <code key={f} className="ml-card__feature" style={{ fontSize: '0.65rem', background: 'var(--gray-bg)', padding: '0.25rem 0.5rem', borderRadius: '6px', color: 'var(--text-mid)' }}>{f}</code>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Fraud score thresholds */}
      <div className="ml-thresholds" style={{ marginTop: '2.5rem', background: 'var(--white)', border: '1.5px solid var(--border)', borderRadius: '24px', padding: '1.5rem 2rem' }}>
        <p className="ml-thresholds__label" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1rem', color: 'var(--text-dark)', marginBottom: '1.25rem' }}>Fraud score decision thresholds</p>
        <div className="ml-thresholds__row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
          {thresholds.map(t => (
            <div key={t.label} className="ml-threshold-item" style={{ borderLeft: `4px solid ${t.color}`, paddingLeft: '1rem' }}>
              <span className="ml-threshold-item__range" style={{ fontSize: '1.1rem', fontWeight: 900, color: t.color, display: 'block' }}>{t.range}</span>
              <span className="ml-threshold-item__label" style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-mid)', textTransform: 'uppercase' }}>{t.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
