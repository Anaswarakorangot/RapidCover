// frontend/src/components/admin/FraudQueuePanel.jsx
// Fraud queue with bulk-reject button
// Replaces/enhances the existing ClaimsQueue for the fraud-specific view

import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const DEMO_FRAUD_QUEUE = [
  {
    claim_id: 'CLM-8842', partner_id: 'ZPT-441892', zone: 'Anand Vihar', zone_code: 'DEL-044',
    trigger: 'AQI Spike', fraud_score: 0.91, flags: ['centroid_drift', 'device_fingerprint'],
    amount: 500, timestamp: '2024-01-15T14:22:00Z', status: 'auto_reject', cluster: 'collusion-ring-A',
  },
  {
    claim_id: 'CLM-8843', partner_id: 'ZPT-441893', zone: 'Anand Vihar', zone_code: 'DEL-044',
    trigger: 'AQI Spike', fraud_score: 0.88, flags: ['device_fingerprint', 'claim_frequency'],
    amount: 500, timestamp: '2024-01-15T14:23:00Z', status: 'manual_queue', cluster: 'collusion-ring-A',
  },
  {
    claim_id: 'CLM-8844', partner_id: 'ZPT-441894', zone: 'Anand Vihar', zone_code: 'DEL-044',
    trigger: 'AQI Spike', fraud_score: 0.85, flags: ['gps_coherence', 'centroid_drift'],
    amount: 500, timestamp: '2024-01-15T14:23:00Z', status: 'manual_queue', cluster: 'collusion-ring-A',
  },
  {
    claim_id: 'CLM-8801', partner_id: 'BLK-229031', zone: 'Bellandur', zone_code: 'BLR-089',
    trigger: 'Rain', fraud_score: 0.78, flags: ['gps_coherence'],
    amount: 400, timestamp: '2024-01-15T11:05:00Z', status: 'manual_queue', cluster: null,
  },
  {
    claim_id: 'CLM-8812', partner_id: 'ZPT-119283', zone: 'Dadar', zone_code: 'MUM-034',
    trigger: 'Rain', fraud_score: 0.76, flags: ['run_count_check'],
    amount: 400, timestamp: '2024-01-15T10:41:00Z', status: 'manual_queue', cluster: null,
  },
];

const FLAG_LABELS = {
  centroid_drift:     { label: 'GPS drift', color: '#9333ea' },
  device_fingerprint: { label: 'Device match', color: 'var(--error)' },
  claim_frequency:    { label: 'Freq spike', color: 'var(--warning)' },
  gps_coherence:      { label: 'GPS incoherent', color: '#0891b2' },
  run_count_check:    { label: 'Run count', color: 'var(--green-primary)' },
  zone_polygon:       { label: 'Zone mismatch', color: 'var(--text-light)' },
};

function scoreColor(score) {
  if (score > 0.90) return 'var(--error)';
  if (score > 0.75) return 'var(--warning)';
  return '#f59e0b';
}

function scoreLabel(score) {
  if (score > 0.90) return 'AUTO-REJECT';
  if (score > 0.75) return 'MANUAL QUEUE';
  return 'ENHANCED CHECK';
}

export default function FraudQueuePanel() {
  const [queue, setQueue] = useState(DEMO_FRAUD_QUEUE);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [actionLog, setActionLog] = useState([]);

  useEffect(() => {
    fetchQueue();
    const t = setInterval(fetchQueue, 20000);
    return () => clearInterval(t);
  }, []);

  async function fetchQueue() {
    try {
      const res = await fetch(`${API_BASE}/admin/panel/fraud-queue`);
      if (res.ok) {
        const data = await res.json();
        if (data.claims?.length) setQueue(data.claims);
      }
    } catch { /* use demo */ }
  }

  function toggleSelect(id) {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function selectCluster(cluster) {
    const ids = queue.filter(c => c.cluster === cluster).map(c => c.claim_id);
    setSelected(prev => new Set([...prev, ...ids]));
  }

  function selectAll() {
    setSelected(new Set(queue.map(c => c.claim_id)));
  }

  function clearSelection() {
    setSelected(new Set());
  }

  async function bulkAction(action) {
    if (selected.size === 0) return;
    setLoading(true);

    const ids = [...selected];
    try {
      await fetch(`${API_BASE}/claims/bulk-${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ claim_ids: ids }),
      });
    } catch { /* backend not yet wired */ }

    // Optimistic update
    setQueue(prev => prev.filter(c => !selected.has(c.claim_id)));
    setActionLog(prev => [
      { action, ids, count: ids.length, time: new Date().toLocaleTimeString('en-IN') },
      ...prev.slice(0, 4),
    ]);
    setSelected(new Set());
    setLoading(false);
  }

  // Group by cluster for collusion ring detection display
  const clusters = [...new Set(queue.filter(c => c.cluster).map(c => c.cluster))];
  const manualQueue = queue.filter(c => c.status === 'manual_queue');
  const autoRejected = queue.filter(c => c.status === 'auto_reject');

  return (
    <section className="fraud-panel">
      <div className="fraud-panel__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <h2 className="fraud-panel__title" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)' }}>{'\u{1F50D}'} Fraud Queue</h2>
          <p className="fraud-panel__subtitle" style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.4rem' }}>
            {manualQueue.length} pending manual review &nbsp;&middot;&nbsp; {autoRejected.length} auto-rejected
            {clusters.length > 0 && <span className="fraud-cluster-badge" style={{ color: 'var(--error)', fontWeight: 700, marginLeft: '0.5rem' }}>{'\u26A0\uFE0F'} {clusters.length} Collision Clusters</span>}
          </p>
        </div>

        {/* Bulk action controls */}
        <div className="fraud-bulk-controls" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="fraud-bulk-selected" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--green-primary)' }}>
            {selected.size > 0 ? `${selected.size} claims selected` : ''}
          </span>
          <button 
            className="fraud-bulk-btn" 
            onClick={selectAll}
            style={{ padding: '0.5rem 1rem', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 800, background: 'var(--gray-bg)', border: '1px solid var(--border)', cursor: 'pointer' }}
          >
            Select all
          </button>
          {selected.size > 0 && (
            <>
              <button 
                className="fraud-bulk-btn" 
                onClick={clearSelection}
                style={{ padding: '0.5rem 1rem', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 800, background: 'transparent', border: '1.5px solid var(--border)', cursor: 'pointer' }}
              >
                Clear
              </button>
              <button
                className="fraud-bulk-btn"
                onClick={() => bulkAction('approve')}
                disabled={loading}
                style={{ padding: '0.5rem 1rem', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 800, background: 'var(--green-primary)', color: 'white', border: 'none', cursor: 'pointer' }}
              >
                Approve ({selected.size})
              </button>
              <button
                className="fraud-bulk-btn"
                onClick={() => bulkAction('reject')}
                disabled={loading}
                style={{ padding: '0.5rem 1rem', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 800, background: 'var(--error)', color: 'white', border: 'none', cursor: 'pointer' }}
              >
                Reject ({selected.size})
              </button>
            </>
          )}
        </div>
      </div>

      {/* Collusion cluster alerts */}
      {clusters.map(cluster => {
        const clusterClaims = queue.filter(c => c.cluster === cluster);
        return (
          <div 
            key={cluster} 
            className="fraud-cluster-alert" 
            style={{ 
              background: '#fef2f2', 
              border: '1.5px solid var(--error)', 
              borderRadius: '18px', 
              padding: '1.25rem', 
              marginBottom: '1.5rem', 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center' 
            }}
          >
            <div className="fraud-cluster-alert__info" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <span style={{ fontSize: '1.75rem' }}>🚨</span>
              <div>
                <strong style={{ fontFamily: 'Nunito', fontSize: '1.1rem', color: '#991b1b' }}>Collusion cluster: {cluster}</strong>
                <p style={{ fontSize: '0.85rem', color: '#991b1b', margin: '0.2rem 0 0' }}>{clusterClaims.length} claims · same zone · same device footprint · suspicious frequency</p>
              </div>
            </div>
            <button
                className="fraud-bulk-btn"
                onClick={() => { selectCluster(cluster); }}
                style={{ padding: '0.6rem 1.25rem', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 800, background: 'var(--error)', color: 'white', border: 'none', cursor: 'pointer' }}
            >
              Bulk Select - Review
            </button>
          </div>
        );
      })}

      {/* Queue table */}
      {queue.length === 0 ? (
        <div className="fraud-empty" style={{ textAlign: 'center', padding: '4rem 0', background: 'var(--gray-bg)', borderRadius: '24px', border: '1.5px solid var(--border)' }}>
          <p style={{ fontFamily: 'Nunito', fontWeight: 800, fontSize: '1.2rem', color: 'var(--text-mid)' }}>Queue is clear</p>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.5rem' }}>All suspicious claims have been processed.</p>
        </div>
      ) : (
        <div className="fraud-table-wrapper" style={{ background: 'var(--white)', borderRadius: '24px', border: '1.5px solid var(--border)', overflow: 'hidden' }}>
          <table className="fraud-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead style={{ background: 'var(--gray-bg)', borderBottom: '1.5px solid var(--border)' }}>
              <tr>
                <th style={{ padding: '1rem' }}><input type="checkbox" onChange={e => e.target.checked ? selectAll() : clearSelection()} /></th>
                <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Claim ID</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Partner</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Zone</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Trigger</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Fraud Score</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Flags</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Amount</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {queue.map(c => {
                const isSelected = selected.has(c.claim_id);
                const color = scoreColor(c.fraud_score);
                return (
                  <tr
                    key={c.claim_id}
                    className={`fraud-table__row ${isSelected ? 'fraud-table__row--selected' : ''}`}
                    style={{ borderBottom: '1px solid var(--border)', background: isSelected ? 'var(--green-light)' : 'transparent', transition: 'all 0.15s' }}
                  >
                    <td style={{ padding: '1rem', textAlign: 'center' }}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(c.claim_id)}
                      />
                    </td>
                    <td style={{ padding: '1rem' }}>
                      <code style={{ fontWeight: 800, color: 'var(--text-dark)' }}>{c.claim_id}</code>
                      {c.drill_id && (
                        <span style={{ marginLeft: '0.4rem', fontSize: '0.6rem', fontWeight: 700, padding: '0.15rem 0.35rem', borderRadius: '4px', background: '#378ADD20', color: '#378ADD', border: '1px solid #378ADD30' }}>
                          DRILL
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '1rem' }}><code style={{ fontSize: '0.75rem' }}>{c.partner_id}</code></td>
                    <td style={{ padding: '1rem' }}>
                      <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{c.zone}</div>
                      <code style={{ fontSize: '0.65rem', color: 'var(--text-light)' }}>{c.zone_code}</code>
                    </td>
                    <td style={{ padding: '1rem', fontSize: '0.85rem' }}>{c.trigger}</td>
                    <td style={{ padding: '1rem' }}>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontWeight: 900, fontSize: '1rem', color }}>{c.fraud_score.toFixed(2)}</span>
                        <span style={{ fontSize: '0.6rem', fontWeight: 800, color, textTransform: 'uppercase' }}>{scoreLabel(c.fraud_score)}</span>
                      </div>
                    </td>
                    <td style={{ padding: '1rem' }}>
                      <div className="fraud-flags" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                        {c.flags.map(f => {
                          const fl = FLAG_LABELS[f] || { label: f, color: 'var(--text-mid)' };
                          return (
                            <span key={f} style={{ fontSize: '0.6rem', fontWeight: 800, padding: '0.2rem 0.5rem', borderRadius: '6px', background: fl.color + '15', color: fl.color, border: `1px solid ${fl.color}25` }}>
                              {fl.label}
                            </span>
                          );
                        })}
                      </div>
                    </td>
                    <td style={{ padding: '1rem', fontWeight: 800 }}>₹{c.amount}</td>
                    <td style={{ padding: '1rem' }}>
                      <div className="fraud-row-actions" style={{ display: 'flex', gap: '0.5rem' }}>
                        <button 
                          style={{ width: 30, height: 30, borderRadius: '8px', border: '1.5px solid var(--green-primary)', background: 'transparent', color: 'var(--green-primary)', cursor: 'pointer', fontWeight: 900 }}
                          onClick={() => { setSelected(new Set([c.claim_id])); bulkAction('approve'); }}
                        >
                          ✓
                        </button>
                        <button 
                          style={{ width: 30, height: 30, borderRadius: '8px', border: '1.5px solid var(--error)', background: 'transparent', color: 'var(--error)', cursor: 'pointer', fontWeight: 900 }}
                          onClick={() => { setSelected(new Set([c.claim_id])); bulkAction('reject'); }}
                        >
                          ✕
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Action log */}
      {actionLog.length > 0 && (
        <div className="fraud-action-log" style={{ marginTop: '1.5rem', background: 'var(--gray-bg)', border: '1.5px solid var(--border)', borderRadius: '18px', padding: '1rem' }}>
          <p style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-light)', marginBottom: '0.5rem' }}>Session History</p>
          {actionLog.map((l, i) => (
            <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-mid)', padding: '0.2rem 0', borderBottom: '1px solid rgba(0,0,0,0.03)' }}>
              <span style={{ fontWeight: 700 }}>{l.time}</span> &nbsp;—&nbsp; {l.action === 'reject' ? <span style={{ color: 'var(--error)' }}>Rejected</span> : <span style={{ color: 'var(--green-primary)' }}>Approved</span>} <strong>{l.count}</strong> claim{l.count > 1 ? 's' : ''}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
