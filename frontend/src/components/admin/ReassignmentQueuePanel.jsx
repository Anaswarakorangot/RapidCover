// frontend/src/components/admin/ReassignmentQueuePanel.jsx
// Dynamic reassignment proof panel — fetches live data from backend

import { useState, useEffect } from 'react';
import { AdminLoader, AdminError, AdminEmpty, ProofCard } from './AdminProofShared';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function ReassignmentQueuePanel() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  
  // New manual action state
  const [partnerId, setPartnerId] = useState('');
  const [targetZone, setTargetZone] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);

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

  async function handlePropose(e) {
    e.preventDefault();
    setActionLoading(true);
    setActionMsg(null);
    try {
      const res = await fetch(`${API}/zones/reassignments/propose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          partner_id: parseInt(partnerId, 10),
          new_zone_id: parseInt(targetZone, 10),
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`);
      setActionMsg({ type: 'success', text: `Proposal initialized successfully for Partner ID ${partnerId}!` });
      load(); // refresh metrics
      setPartnerId('');
      setTargetZone('');
    } catch (err) {
      setActionMsg({ type: 'error', text: err.message });
    } finally {
      setActionLoading(false);
    }
  }

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
      
      {/* Admin Quick Action */}
      <div style={{ marginBottom: "1.5rem", padding: "16px", background: "#f9fafb", borderRadius: "12px", border: "1px solid #e5e7eb" }}>
        <p className="proof-detail-section-label" style={{ marginBottom: "12px", color: "var(--green-primary)" }}>
          Admin Action: Propose New Zone Reassignment
        </p>
        <form onSubmit={handlePropose} style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          <input 
            type="number" 
            placeholder="Partner ID" 
            value={partnerId}
            onChange={e => setPartnerId(e.target.value)}
            style={{ padding: "8px 12px", borderRadius: "8px", border: "1px solid #d1d5db" }}
            required
            min="1"
          />
          <input 
            type="number" 
            placeholder="Target Zone ID" 
            value={targetZone}
            onChange={e => setTargetZone(e.target.value)}
            style={{ padding: "8px 12px", borderRadius: "8px", border: "1px solid #d1d5db" }}
            required
            min="1"
          />
          <button 
            type="submit" 
            disabled={actionLoading}
            style={{ 
              padding: "8px 16px", borderRadius: "8px", background: "var(--green-primary)",
              color: "white", fontWeight: "600", border: "none", cursor: actionLoading ? "not-allowed" : "pointer" 
            }}>
            {actionLoading ? 'Proposing...' : 'Submit Proposal'}
          </button>
        </form>
        {actionMsg && (
          <p style={{ marginTop: "10px", fontSize: "13px", fontWeight: "600", color: actionMsg.type === 'error' ? 'var(--danger)' : 'var(--green-primary)' }}>
            {actionMsg.text}
          </p>
        )}
      </div>
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
