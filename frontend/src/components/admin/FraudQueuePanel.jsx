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
  device_fingerprint: { label: 'Device match', color: '#dc2626' },
  claim_frequency:    { label: 'Freq spike', color: '#d97706' },
  gps_coherence:      { label: 'GPS incoherent', color: '#0891b2' },
  run_count_check:    { label: 'Run count', color: '#059669' },
  zone_polygon:       { label: 'Zone mismatch', color: '#64748b' },
};

function scoreColor(score) {
  if (score > 0.90) return '#dc3545';
  if (score > 0.75) return '#fd7e14';
  return '#ffc107';
}

function scoreLabel(score) {
  if (score > 0.90) return 'Auto-reject';
  if (score > 0.75) return 'Manual queue';
  return 'Enhanced check';
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
      <div className="fraud-panel__header">
        <div>
          <h2 className="fraud-panel__title">{'\u{1F50D}'} Fraud Queue</h2>
          <p className="fraud-panel__subtitle">
            {manualQueue.length} pending manual review &nbsp;&middot;&nbsp; {autoRejected.length} auto-rejected
            {clusters.length > 0 && <span className="fraud-cluster-badge"> &nbsp;Warning: {clusters.length} collusion cluster{clusters.length > 1 ? 's' : ''} detected</span>}
          </p>
        </div>

        {/* Bulk action controls */}
        <div className="fraud-bulk-controls">
          <span className="fraud-bulk-selected">
            {selected.size > 0 ? `${selected.size} selected` : ''}
          </span>
          <button className="fraud-bulk-btn fraud-bulk-btn--select-all" onClick={selectAll}>Select all</button>
          {selected.size > 0 && (
            <>
              <button className="fraud-bulk-btn fraud-bulk-btn--clear" onClick={clearSelection}>Clear</button>
              <button
                className="fraud-bulk-btn fraud-bulk-btn--approve"
                onClick={() => bulkAction('approve')}
                disabled={loading}
              >
                Approve {selected.size}
              </button>
              <button
                className="fraud-bulk-btn fraud-bulk-btn--reject"
                onClick={() => bulkAction('reject')}
                disabled={loading}
              >
                Reject {selected.size}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Collusion cluster alerts */}
      {clusters.map(cluster => {
        const clusterClaims = queue.filter(c => c.cluster === cluster);
        return (
          <div key={cluster} className="fraud-cluster-alert">
            <div className="fraud-cluster-alert__info">
              <span>🚨</span>
              <div>
                <strong>Collusion cluster detected: {cluster}</strong>
                <p>{clusterClaims.length} claims - same zone - same event - same device profile</p>
              </div>
            </div>
            <button
              className="fraud-bulk-btn fraud-bulk-btn--reject"
              onClick={() => { selectCluster(cluster); }}
            >
              Select cluster - Bulk reject
            </button>
          </div>
        );
      })}

      {/* Queue table */}
      {queue.length === 0 ? (
        <div className="fraud-empty">
          <p>Fraud queue is clear</p>
          {actionLog.length > 0 && (
            <div className="fraud-action-log">
              {actionLog.map((l, i) => (
                <p key={i} className="fraud-action-log__item">
                  {l.time} -- {l.action === 'reject' ? 'Rejected' : 'Approved'} {l.count} claim{l.count > 1 ? 's' : ''}
                </p>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="fraud-table-wrapper">
          <table className="fraud-table">
            <thead>
              <tr>
                <th><input type="checkbox" onChange={e => e.target.checked ? selectAll() : clearSelection()} /></th>
                <th>Claim ID</th>
                <th>Partner</th>
                <th>Zone</th>
                <th>Trigger</th>
                <th>Fraud Score</th>
                <th>Flags</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {queue.map(c => {
                const isSelected = selected.has(c.claim_id);
                const color = scoreColor(c.fraud_score);
                return (
                  <tr
                    key={c.claim_id}
                    className={`fraud-table__row ${isSelected ? 'fraud-table__row--selected' : ''} ${c.cluster ? 'fraud-table__row--cluster' : ''}`}
                  >
                    <td>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(c.claim_id)}
                      />
                    </td>
                    <td><code className="fraud-claim-id">{c.claim_id}</code></td>
                    <td><code>{c.partner_id}</code></td>
                    <td>
                      <span>{c.zone}</span>
                      <code className="fraud-zone-code">{c.zone_code}</code>
                    </td>
                    <td>{c.trigger}</td>
                    <td>
                      <div className="fraud-score-cell">
                        <span className="fraud-score-num" style={{ color }}>{c.fraud_score.toFixed(2)}</span>
                        <span className="fraud-score-label" style={{ color }}>{scoreLabel(c.fraud_score)}</span>
                      </div>
                    </td>
                    <td>
                      <div className="fraud-flags">
                        {c.flags.map(f => {
                          const fl = FLAG_LABELS[f] || { label: f, color: '#64748b' };
                          return (
                            <span key={f} className="fraud-flag" style={{ background: fl.color + '22', color: fl.color }}>
                              {fl.label}
                            </span>
                          );
                        })}
                      </div>
                    </td>
                    <td>Rs.{c.amount}</td>
                    <td>
                      <span className={`fraud-status fraud-status--${c.status === 'auto_reject' ? 'reject' : 'queue'}`}>
                        {c.status === 'auto_reject' ? 'Auto-rejected' : 'Manual review'}
                      </span>
                    </td>
                    <td>
                      <div className="fraud-row-actions">
                        <button className="fraud-row-btn fraud-row-btn--approve" onClick={() => { setSelected(new Set([c.claim_id])); bulkAction('approve'); }}>{'\u2713'}</button>
                        <button className="fraud-row-btn fraud-row-btn--reject"  onClick={() => { setSelected(new Set([c.claim_id])); bulkAction('reject');  }}>{'\u2715'}</button>
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
      {actionLog.length > 0 && queue.length > 0 && (
        <div className="fraud-action-log">
          {actionLog.map((l, i) => (
            <p key={i} className="fraud-action-log__item">
              {l.time} -- {l.action === 'reject' ? 'Rejected' : 'Approved'} {l.count} claim{l.count > 1 ? 's' : ''}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
