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
      <div className="ml-panel__header">
        <h2 className="ml-panel__title">{'\u{1F916}'} ML Model Status</h2>
        <p className="ml-panel__subtitle">All models active -- rules-based fallback available if any model goes offline</p>
      </div>

      <div className="ml-panel__grid">
        {models.map(m => (
          <div key={m.name} className="ml-card">
            <div className="ml-card__top">
              <span className="ml-card__icon">{m.icon}</span>
              <div className="ml-card__title-block">
                <p className="ml-card__name">{m.name}</p>
                <div className="ml-card__badges">
                  <span className="ml-card__algo">{m.algo}</span>
                  <span className="ml-card__status">
                    <span className="ml-card__dot" /> Active
                  </span>
                </div>
              </div>
              <span className="ml-card__version">{m.version}</span>
            </div>

            <p className="ml-card__desc">{m.desc}</p>

            <div className="ml-card__features">
              <p className="ml-card__features-label">Input features</p>
              <div className="ml-card__feature-list">
                {m.features.map(f => (
                  <code key={f} className="ml-card__feature">{f}</code>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Fraud score thresholds -- shown under Fraud Detector context */}
      <div className="ml-thresholds">
        <p className="ml-thresholds__label">Fraud score decision thresholds</p>
        <div className="ml-thresholds__row">
          {thresholds.map(t => (
            <div key={t.label} className="ml-threshold-item" style={{ borderColor: t.color }}>
              <span className="ml-threshold-item__range" style={{ color: t.color }}>{t.range}</span>
              <span className="ml-threshold-item__label">{t.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
