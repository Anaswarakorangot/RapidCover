// frontend/src/components/admin/VerificationPanel.jsx
// Real-World Validation Matrix — shows all 10 pre-payout checks per claim

import { useState, useEffect } from 'react';
import { AdminLoader, AdminError, AdminEmpty } from './AdminProofShared';
import { authenticatedFetch } from '../../services/adminApi';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const CHECK_META = {
  source_threshold_breach: { icon: '📡', label: 'Source Threshold Breach' },
  zone_match: { icon: '🗺️', label: 'Zone Match' },
  pin_code_match: { icon: '📍', label: 'Pin-Code Match' },
  active_policy: { icon: '📋', label: 'Active Policy' },
  shift_window: { icon: '🕐', label: 'Shift Window' },
  partner_activity: { icon: '👤', label: 'Partner Activity' },
  platform_activity: { icon: '📱', label: 'Platform Activity' },
  fraud_score_below_threshold: { icon: '🔍', label: 'Fraud Score' },
  data_freshness: { icon: '⏱️', label: 'Data Freshness' },
  cross_source_agreement: { icon: '🤝', label: 'Cross-Source Agreement' },
};

export default function VerificationPanel() {
  const [proofData, setProofData] = useState(null);
  const [claimMatrix, setClaimMatrix] = useState(null);
  const [claimId, setClaimId] = useState('');
  const [loadingProof, setLoadingProof] = useState(true);
  const [loadingClaim, setLoadingClaim] = useState(false);
  const [error, setError] = useState(null);
  const [claimError, setClaimError] = useState(null);

  useEffect(() => { loadProof(); }, []);

  async function loadProof() {
    setLoadingProof(true); setError(null);
    try {
      const res = await authenticatedFetch(`${API}/admin/panel/proof/validation-matrix`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setProofData(await res.json());
    } catch (e) { setError(e.message); }
    finally { setLoadingProof(false); }
  }

  async function loadClaimMatrix() {
    if (!claimId) return;
    setLoadingClaim(true); setClaimError(null);
    try {
      const res = await authenticatedFetch(`${API}/admin/claims/${claimId}/validation-matrix`);
      if (!res.ok) throw new Error(`HTTP ${res.status} — claim not found`);
      setClaimMatrix(await res.json());
    } catch (e) { setClaimError(e.message); setClaimMatrix(null); }
    finally { setLoadingClaim(false); }
  }

  const matrix = claimMatrix?.validation_matrix || proofData?.matrix || [];
  const summary = claimMatrix
    ? claimMatrix.matrix_summary
    : proofData?.matrix_summary;

  return (
    <section>
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)' }}>
          🔍 Validation Matrix
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-light)', marginTop: '0.3rem' }}>
          10-check pre-payout audit trail. Every claim carries a machine-readable validation matrix.
        </p>
      </div>

      {/* Claim ID lookup */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', padding: '1rem', background: 'var(--white)', borderRadius: '14px', border: '1.5px solid var(--border)' }}>
        <input
          type="number"
          placeholder="Enter Claim ID to inspect…"
          value={claimId}
          onChange={e => setClaimId(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && loadClaimMatrix()}
          style={{ flex: 1, padding: '0.6rem 0.9rem', borderRadius: '10px', border: '1.5px solid var(--border)', fontSize: '0.9rem' }}
        />
        <button
          onClick={loadClaimMatrix}
          disabled={!claimId || loadingClaim}
          style={{ padding: '0.6rem 1.25rem', borderRadius: '10px', background: (!claimId || loadingClaim) ? 'var(--text-light)' : 'var(--primary)', color: 'white', border: 'none', fontWeight: 800, fontSize: '0.85rem', cursor: (!claimId || loadingClaim) ? 'not-allowed' : 'pointer' }}
        >
          {loadingClaim ? 'Loading…' : 'Inspect Claim'}
        </button>
        {claimMatrix && (
          <button onClick={() => { setClaimMatrix(null); setClaimId(''); }}
            style={{ padding: '0.6rem 1rem', borderRadius: '10px', background: 'var(--gray-bg)', color: 'var(--text-mid)', border: '1.5px solid var(--border)', fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer' }}>
            ✕ Clear
          </button>
        )}
      </div>

      {claimError && (
        <div style={{ padding: '0.75rem 1rem', background: '#fef2f2', borderRadius: '10px', color: '#991b1b', fontSize: '0.85rem', marginBottom: '1rem' }}>
          ⚠️ {claimError}
        </div>
      )}

      {/* Summary counters */}
      {summary && (
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          {[
            { label: 'Total Checks', value: summary.total_checks ?? 10, color: 'var(--primary)' },
            { label: 'Passed', value: summary.passed ?? 0, color: 'var(--green-primary)' },
            { label: 'Failed', value: summary.failed ?? 0, color: 'var(--error)' },
          ].map(m => (
            <div key={m.label} style={{ flex: 1, minWidth: 110, padding: '1rem', borderRadius: '14px', background: 'var(--white)', border: `2px solid ${m.color}30`, textAlign: 'center' }}>
              <div style={{ fontSize: '1.75rem', fontWeight: 900, color: m.color, fontFamily: 'Nunito' }}>{m.value}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-light)', fontWeight: 700, textTransform: 'uppercase', marginTop: '0.2rem' }}>{m.label}</div>
            </div>
          ))}
          {claimMatrix && (
            <div style={{ flex: 1, minWidth: 110, padding: '1rem', borderRadius: '14px', background: 'var(--white)', border: '1.5px solid var(--border)', textAlign: 'center' }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 900, color: 'var(--text-dark)', fontFamily: 'Nunito' }}>#{claimMatrix.claim_id}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-light)', fontWeight: 700, textTransform: 'uppercase', marginTop: '0.2rem' }}>
                {claimMatrix.claim_status} · ₹{claimMatrix.claim_amount}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Matrix rows */}
      {loadingProof && !claimMatrix ? (
        <AdminLoader message="Loading validation matrix…" />
      ) : error && !claimMatrix ? (
        <AdminError message={error} onRetry={loadProof} />
      ) : matrix.length === 0 ? (
        <AdminEmpty icon="📋" message="No matrix yet — fire a trigger to generate a claim." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {matrix.map((check, i) => <MatrixRow key={check.check_name || i} check={check} />)}
        </div>
      )}

      {/* Footer note */}
      {proofData && !claimMatrix && (
        <div style={{ marginTop: '1.5rem', padding: '0.75rem 1rem', background: 'var(--gray-bg)', borderRadius: '10px', fontSize: '0.78rem', color: 'var(--text-light)' }}>
          Showing matrix from claim #{proofData.sample_claim_id} ({proofData.sample_claim_status}).
          Enter any Claim ID above to inspect a specific claim.
        </div>
      )}
    </section>
  );
}

function MatrixRow({ check }) {
  const { check_name, passed, reason, source, confidence } = check;
  const meta = CHECK_META[check_name] || { icon: '•', label: check_name?.replace(/_/g, ' ') };
  const confPct = Math.round((confidence ?? 0) * 100);
  const confColor = confPct >= 80 ? 'var(--green-primary)' : confPct >= 40 ? '#f59e0b' : 'var(--error)';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '1rem',
      padding: '0.875rem 1rem', background: 'var(--white)',
      borderRadius: '12px', border: '1.5px solid var(--border)',
      borderLeft: `4px solid ${passed ? 'var(--green-primary)' : 'var(--error)'}`,
    }}>
      <div style={{
        width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
        background: passed ? 'var(--green-light)' : '#fef2f2',
        border: `2px solid ${passed ? 'var(--green-primary)' : 'var(--error)'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '0.8rem', fontWeight: 900, color: passed ? 'var(--green-dark)' : '#991b1b',
      }}>
        {passed ? '✓' : '✕'}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 210 }}>
        <span style={{ fontSize: '1rem' }}>{meta.icon}</span>
        <span style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dark)' }}>{meta.label}</span>
      </div>
      <div style={{ flex: 1, fontSize: '0.8rem', color: 'var(--text-mid)' }}>{reason}</div>
      <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '2px 8px', borderRadius: '8px', background: 'var(--gray-bg)', color: 'var(--text-light)', whiteSpace: 'nowrap' }}>
        {source}
      </span>
      <div style={{ width: 80, flexShrink: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '2px', color: 'var(--text-light)' }}>
          <span>conf</span>
          <span style={{ color: confColor, fontWeight: 700 }}>{confPct}%</span>
        </div>
        <div style={{ height: 5, background: 'var(--gray-bg)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ width: `${confPct}%`, height: '100%', background: confColor, borderRadius: 3 }} />
        </div>
      </div>
    </div>
  );
}