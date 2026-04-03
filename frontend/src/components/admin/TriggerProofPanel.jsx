// frontend/src/components/admin/TriggerProofPanel.jsx
// Dynamic trigger eligibility proof — pin-code strictness checks

import { useState, useEffect } from 'react';
import { AdminLoader, AdminError, AdminEmpty, ProofCard } from './AdminProofShared';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

function Bar({ label, filled, total, color = 'var(--green-primary)' }) {
  const pct = total > 0 ? Math.round((filled / total) * 100) : 0;
  return (
    <div style={{ marginBottom: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.3rem' }}>
        <span>{label}</span>
        <span>{filled}/{total} ({pct}%)</span>
      </div>
      <div style={{ height: 10, background: 'var(--gray-bg)', borderRadius: 5, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 5, transition: 'width 0.8s ease' }} />
      </div>
    </div>
  );
}

export default function TriggerProofPanel() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/admin/panel/proof/trigger-eligibility`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <AdminLoader message="Checking trigger eligibility…" />;
  if (error)   return <AdminError message={error} onRetry={load} />;
  if (!data)   return <AdminEmpty icon="🎯" message="No eligibility data" />;

  const { input, output, timestamps, source, pass_fail, notes } = data;

  return (
    <ProofCard
      title="🎯 Trigger Eligibility Proof"
      subtitle="Pin-code strictness enforcement — partner & zone coverage validation"
      timestamp={timestamps?.computed_at}
      source={source}
      passFail={pass_fail}
    >
      {/* Metrics */}
      <div className="proof-metrics-grid">
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">Partners Checked</span>
          <span className="proof-metric-card__value">{input?.partners_checked ?? 0}</span>
        </div>
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">Zones Checked</span>
          <span className="proof-metric-card__value">{input?.zones_checked ?? 0}</span>
        </div>
      </div>

      {/* Visual bars */}
      <div style={{ marginTop: '1.5rem' }}>
        <p className="proof-detail-section-label">COVERAGE ANALYSIS</p>
        <Bar
          label="Partners with Pin Code"
          filled={output?.partners_with_pin_code ?? 0}
          total={input?.partners_checked ?? 0}
          color="var(--green-primary)"
        />
        <Bar
          label="Partners without Pin Code"
          filled={output?.partners_without_pin_code ?? 0}
          total={input?.partners_checked ?? 0}
          color="var(--error)"
        />
        <Bar
          label="Zones with Coverage Data"
          filled={output?.zones_with_coverage_data ?? 0}
          total={input?.zones_checked ?? 0}
          color="var(--green-primary)"
        />
        <Bar
          label="Zones without Coverage Data"
          filled={output?.zones_without_coverage_data ?? 0}
          total={input?.zones_checked ?? 0}
          color="var(--warning)"
        />
      </div>

      {/* Notes */}
      {notes?.length > 0 && (
        <div className="proof-notes" style={{ marginTop: '1.5rem' }}>
          <p className="proof-detail-section-label">ENFORCEMENT RULES</p>
          <ul className="proof-assumptions-list">
            {notes.map((n, i) => <li key={i}>{n}</li>)}
          </ul>
        </div>
      )}
    </ProofCard>
  );
}
