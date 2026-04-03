// frontend/src/components/admin/ReassignmentQueuePanel.jsx
// Dynamic reassignment proof panel — fetches live data from backend

import { useState, useEffect } from 'react';
import { AdminLoader, AdminError, AdminEmpty, ProofCard } from './AdminProofShared';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function ReassignmentQueuePanel() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/admin/panel/proof/reassignments`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <AdminLoader message="Loading reassignment queue…" />;
  if (error)   return <AdminError message={error} onRetry={load} />;
  if (!data)   return <AdminEmpty icon="🔄" message="No reassignment data" />;

  const { output, timestamps, source, pass_fail, notes } = data;

  return (
    <ProofCard
      title="🔄 Zone Reassignment Queue"
      subtitle="24-hour acceptance workflow — proposals, expirations, and state machine"
      timestamp={timestamps?.computed_at}
      source={source}
      passFail={pass_fail}
    >
      {/* Metrics grid */}
      <div className="proof-metrics-grid">
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">Total Proposals</span>
          <span className="proof-metric-card__value">{output?.total ?? 0}</span>
        </div>
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">Pending</span>
          <span className="proof-metric-card__value" style={{ color: output?.pending_count > 0 ? 'var(--warning)' : 'var(--green-primary)' }}>
            {output?.pending_count ?? 0}
          </span>
        </div>
        <div className="proof-metric-card">
          <span className="proof-metric-card__label">Expired This Check</span>
          <span className="proof-metric-card__value">{output?.expired_this_check ?? 0}</span>
        </div>
      </div>

      {/* State machine diagram */}
      <div className="proof-state-machine">
        <p className="proof-detail-section-label">STATE MACHINE</p>
        <div className="proof-state-flow">
          <div className="proof-state-node proof-state-node--active">proposed</div>
          <div className="proof-state-arrow">→</div>
          <div className="proof-state-node proof-state-node--success">accepted</div>
          <div className="proof-state-arrow">→</div>
          <div className="proof-state-node">zone updated</div>
        </div>
        <div className="proof-state-flow" style={{ marginTop: '0.5rem' }}>
          <div className="proof-state-node proof-state-node--active">proposed</div>
          <div className="proof-state-arrow">→</div>
          <div className="proof-state-node proof-state-node--danger">rejected</div>
        </div>
        <div className="proof-state-flow" style={{ marginTop: '0.5rem' }}>
          <div className="proof-state-node proof-state-node--active">proposed</div>
          <div className="proof-state-arrow">24h →</div>
          <div className="proof-state-node proof-state-node--warn">expired</div>
        </div>
      </div>

      {/* Notes */}
      {notes?.length > 0 && (
        <div className="proof-notes">
          <p className="proof-detail-section-label">NOTES</p>
          <ul className="proof-assumptions-list">
            {notes.map((n, i) => <li key={i}>{n}</li>)}
          </ul>
        </div>
      )}
    </ProofCard>
  );
}
