// frontend/src/components/admin/DemoChecklist.jsx
// Evaluator-facing proof dashboard — aggregates all proof endpoints

import { useState, useEffect } from 'react';
import { AdminLoader, AdminError, ProofCard, SourceBadge, PassFailBadge } from './AdminProofShared';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const PROOF_ENDPOINTS = [
  { id: 'stress',       label: 'Stress Scenarios',        icon: '⚡', endpoint: '/admin/panel/proof/stress' },
  { id: 'reassignments', label: 'Zone Reassignments',     icon: '🔄', endpoint: '/admin/panel/proof/reassignments' },
  { id: 'trigger',      label: 'Trigger Eligibility',     icon: '🎯', endpoint: '/admin/panel/proof/trigger-eligibility' },
  { id: 'riqi',         label: 'RIQI Provenance',         icon: '📊', endpoint: '/admin/panel/proof/riqi' },
  { id: 'data-sources', label: 'Data Sources Inventory',  icon: '🗃️', endpoint: '/admin/panel/proof/data-sources' },
];

export default function DemoChecklist() {
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  async function loadAll() {
    setLoading(true);
    setError(null);
    const newResults = {};

    try {
      await Promise.all(
        PROOF_ENDPOINTS.map(async (ep) => {
          try {
            const res = await fetch(`${API}${ep.endpoint}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            newResults[ep.id] = { status: 'ok', data: await res.json() };
          } catch (e) {
            newResults[ep.id] = { status: 'error', error: e.message };
          }
        })
      );
      setResults(newResults);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []);

  if (loading) return <AdminLoader message="Running all proof checks…" />;
  if (error)   return <AdminError message={error} onRetry={loadAll} />;

  // Calculate overall status
  const allPassed = PROOF_ENDPOINTS.every(ep => {
    const r = results[ep.id];
    return r?.status === 'ok' && (r.data?.pass_fail === 'pass' || ep.id === 'data-sources');
  });
  const anyFailed = PROOF_ENDPOINTS.some(ep => results[ep.id]?.status === 'error');
  const overallStatus = allPassed ? 'pass' : anyFailed ? 'fail' : 'partial';

  const overallLabel = overallStatus === 'pass' ? '✅ Demo Ready'
    : overallStatus === 'fail' ? '❌ Not Ready'
    : '⚠️ Partially Ready';

  const overallColor = overallStatus === 'pass' ? 'var(--green-primary)'
    : overallStatus === 'fail' ? 'var(--error)'
    : 'var(--warning)';

  return (
    <ProofCard
      title="✅ Demo Checklist"
      subtitle="Evaluator-facing single screen — all proof endpoints aggregated"
      passFail={overallStatus}
    >
      {/* Overall status header */}
      <div className="checklist-overall" style={{ borderColor: overallColor }}>
        <span className="checklist-overall__label">Overall Status</span>
        <span className="checklist-overall__value" style={{ color: overallColor }}>{overallLabel}</span>
        <button className="proof-action-btn" onClick={loadAll} style={{ marginLeft: 'auto' }}>
          🔄 Refresh All
        </button>
      </div>

      {/* Feature rows */}
      <div className="checklist-rows">
        {PROOF_ENDPOINTS.map(ep => {
          const r = results[ep.id];
          const isOk = r?.status === 'ok';
          const d = r?.data || {};

          return (
            <div key={ep.id} className={`checklist-row ${isOk ? '' : 'checklist-row--error'}`}>
              <div className="checklist-row__left">
                <span className="checklist-row__icon">{ep.icon}</span>
                <div>
                  <span className="checklist-row__label">{ep.label}</span>
                  <span className="checklist-row__feature">{d.feature || ep.id}</span>
                </div>
              </div>
              <div className="checklist-row__right">
                {isOk ? (
                  <>
                    {d.pass_fail && <PassFailBadge status={d.pass_fail} />}
                    {d.source && <SourceBadge source={d.source} />}
                    <span className="checklist-row__time">
                      {d.timestamps?.computed_at
                        ? new Date(d.timestamps.computed_at).toLocaleTimeString('en-IN')
                        : d.computed_at
                          ? new Date(d.computed_at).toLocaleTimeString('en-IN')
                          : '—'
                      }
                    </span>
                  </>
                ) : (
                  <span className="proof-badge proof-badge--fail">❌ {r?.error || 'Failed'}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Data sources inventory */}
      {results['data-sources']?.status === 'ok' && (
        <div style={{ marginTop: '2rem' }}>
          <p className="proof-detail-section-label">DATA SOURCES INVENTORY</p>
          <div className="proof-table-wrapper">
            <table className="proof-table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Type</th>
                  <th style={{ textAlign: 'right' }}>Rows / Count</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {(results['data-sources'].data.sources || []).map(s => (
                  <tr key={s.name}>
                    <td style={{ fontWeight: 800, fontSize: '0.85rem' }}>{s.name}</td>
                    <td>
                      <span className="proof-type-badge" style={{
                        background: s.type === 'database' ? 'var(--green-light)' : s.type === 'config' ? '#dbeafe' : '#f3e8ff',
                        color: s.type === 'database' ? 'var(--green-dark)' : s.type === 'config' ? '#2563eb' : '#9333ea',
                      }}>
                        {s.type}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>
                      {s.row_count ?? s.scenario_count ?? s.notification_types ?? '—'}
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-mid)' }}>{s.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Proof notes aggregation */}
      <div style={{ marginTop: '1.5rem' }}>
        <p className="proof-detail-section-label">PROOF NOTES</p>
        <div className="proof-notes-aggregate">
          {PROOF_ENDPOINTS.filter(ep => results[ep.id]?.status === 'ok' && results[ep.id].data?.notes?.length > 0).map(ep => (
            <div key={ep.id} className="proof-notes-group">
              <span className="proof-notes-group__label">{ep.icon} {ep.label}</span>
              <ul className="proof-assumptions-list">
                {results[ep.id].data.notes.map((n, i) => <li key={i}>{n}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </ProofCard>
  );
}
