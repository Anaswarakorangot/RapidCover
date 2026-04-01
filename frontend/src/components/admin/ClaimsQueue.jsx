import { useState, useEffect } from 'react';
import api from '../../services/api';

const FRAUD_VECTORS = {
  gps_anomaly: 'GPS trajectory anomaly: speed of 180km/h between two check-ins',
  run_count_anomaly: 'Activity paradox: runs completed during claimed disruption window',
  zone_boundary: 'Zone boundary gaming: GPS centroid 4.2km outside declared dark store',
  duplicate_event: 'Duplicate event: same cryptographic event ID submitted twice',
  collusion_ring: 'Collusion ring: device fingerprint + IP cluster match detected',
  synthetic_identity: 'Synthetic identity: Aadhaar + face liveness check failed',
};

const ANOMALY_REASONS = [
  'gps_anomaly',
  'run_count_anomaly',
  'zone_boundary',
  'duplicate_event',
  'collusion_ring',
  'synthetic_identity',
];

function getFraudBadge(score) {
  if (score >= 0.90) return { label: 'Auto-rejected', cls: 'badge--rejected' };
  if (score >= 0.75) return { label: 'Manual review', cls: 'badge--review' };
  if (score >= 0.50) return { label: 'Enhanced validation', cls: 'badge--validation' };
  return { label: 'Auto-approved', cls: 'badge--approved' };
}

function getTriggerLabel(type) {
  const map = { rain: 'Rain', heat: 'Heat', aqi: 'AQI', shutdown: 'Shutdown', closure: 'Closure' };
  return map[type] || type;
}

// Generate a mock claim ID from zone code and index
function formatClaimId(claim, index) {
  const zoneCode = (claim.zone_name || 'BLR047').replace(/[\s-]/g, '').toUpperCase().slice(0, 6);
  return `RC-${zoneCode}-${String(claim.id || index + 1).padStart(3, '0')}`;
}

// Mock data for demo when backend has no claims yet
const MOCK_CLAIMS = [
  {
    id: 1, partner_name: 'Manoj K', zone_name: 'BLR-047', trigger_type: 'rain',
    amount: 420, fraud_score: 0.82, status: 'pending',
    anomaly: 'gps_anomaly',
  },
  {
    id: 2, partner_name: 'Raju S', zone_name: 'BLR-047', trigger_type: 'rain',
    amount: 600, fraud_score: 0.63, status: 'pending',
    anomaly: 'run_count_anomaly',
  },
  {
    id: 3, partner_name: 'Priya T', zone_name: 'MUM-021', trigger_type: 'heat',
    amount: 350, fraud_score: 0.09, status: 'paid',
    anomaly: null,
  },
  {
    id: 4, partner_name: 'Arun D', zone_name: 'DEL-009', trigger_type: 'aqi',
    amount: 310, fraud_score: 0.91, status: 'rejected',
    anomaly: 'synthetic_identity',
  },
  {
    id: 5, partner_name: 'Sneha M', zone_name: 'BLR-047', trigger_type: 'shutdown',
    amount: 420, fraud_score: 0.12, status: 'paid',
    anomaly: null,
  },
  {
    id: 6, partner_name: 'Vikram R', zone_name: 'MUM-021', trigger_type: 'rain',
    amount: 500, fraud_score: 0.55, status: 'pending',
    anomaly: 'zone_boundary',
  },
];

export default function ClaimsQueue() {
  const [claims, setClaims] = useState([]);
  const [triggerFilter, setTriggerFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);

  useEffect(() => {
    loadClaims();
  }, []);

  async function loadClaims() {
    setLoading(true);
    try {
      const data = await api.getAdminClaims();
      if (data.length > 0) {
        // Enrich with random anomaly reasons for demo
        const enriched = data.map((c, i) => ({
          ...c,
          anomaly: c.fraud_score >= 0.50
            ? ANOMALY_REASONS[i % ANOMALY_REASONS.length]
            : null,
        }));
        setClaims(enriched);
      } else {
        setClaims(MOCK_CLAIMS);
      }
    } catch {
      setClaims(MOCK_CLAIMS);
    } finally {
      setLoading(false);
    }
  }

  async function handleAction(claimId, action) {
    setActionLoading(claimId);
    try {
      if (action === 'approve') {
        await api.approveClaim(claimId);
      } else {
        await api.rejectClaim(claimId, 'Manual rejection by admin');
      }
      // Update inline
      setClaims(prev =>
        prev.map(c =>
          c.id === claimId ? { ...c, status: action === 'approve' ? 'approved' : 'rejected' } : c
        )
      );
    } catch (err) {
      // If backend fails (mock data), just update locally
      setClaims(prev =>
        prev.map(c =>
          c.id === claimId ? { ...c, status: action === 'approve' ? 'approved' : 'rejected' } : c
        )
      );
    } finally {
      setActionLoading(null);
    }
  }

  const filtered = claims.filter(c => {
    if (triggerFilter !== 'all' && c.trigger_type !== triggerFilter) return false;
    if (statusFilter === 'pending') return c.status === 'pending';
    if (statusFilter === 'auto-approved') return c.fraud_score < 0.50 && (c.status === 'approved' || c.status === 'paid');
    if (statusFilter === 'auto-rejected') return c.fraud_score >= 0.90;
    return true;
  });

  return (
    <div className="admin-section" style={{ animationDelay: '0.5s' }}>
      <div className="claims-header">
        <div className="admin-section-label">CLAIMSQUEUE.JSX — FRAUD REVIEW QUEUE</div>
        <div className="claims-filters">
          <select
            className="claims-filter-select"
            value={triggerFilter}
            onChange={e => setTriggerFilter(e.target.value)}
          >
            <option value="all">All triggers</option>
            <option value="rain">Rain</option>
            <option value="heat">Heat</option>
            <option value="aqi">AQI</option>
            <option value="shutdown">Shutdown</option>
            <option value="closure">Closure</option>
          </select>
          <select
            className="claims-filter-select"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="all">All statuses</option>
            <option value="pending">Pending review</option>
            <option value="auto-approved">Auto-approved</option>
            <option value="auto-rejected">Auto-rejected</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="claims-loading">
          <div className="claims-spinner" />
        </div>
      ) : (
        <div className="claims-list">
          {filtered.map((claim, idx) => {
            const badge = getFraudBadge(claim.fraud_score);
            const claimId = formatClaimId(claim, idx);
            const anomalyDetail = claim.anomaly
              ? FRAUD_VECTORS[claim.anomaly] || claim.anomaly
              : null;

            return (
              <div key={claim.id} className="claim-row">
                <div className="claim-row__left">
                  <div className="claim-row__top">
                    <span className="claim-row__id">{claimId}</span>
                    <span className={`claim-badge ${badge.cls}`}>{badge.label}</span>
                    <span className="claim-trigger-badge">{getTriggerLabel(claim.trigger_type)}</span>
                  </div>
                  <div className="claim-row__detail">
                    {claim.partner_name} · {claim.zone_name} · ₹{claim.amount}
                    {anomalyDetail && (
                      <> · <span className="claim-anomaly">{anomalyDetail}</span></>
                    )}
                    {claim.status === 'paid' && <> · <span className="claim-paid-tag">paid</span></>}
                  </div>
                </div>
                <div className="claim-row__right">
                  <div className="claim-fraud-score">
                    <span className="claim-fraud-label">Fraud score</span>
                    <span
                      className="claim-fraud-value"
                      style={{
                        color: claim.fraud_score >= 0.75 ? '#ef4444'
                          : claim.fraud_score >= 0.50 ? '#f97316'
                          : '#22c55e',
                      }}
                    >
                      {claim.fraud_score.toFixed(2)}
                    </span>
                  </div>
                  <div className="claim-actions">
                    {claim.status === 'pending' && claim.fraud_score < 0.90 ? (
                      <>
                        <button
                          className="claim-btn claim-btn--approve"
                          onClick={() => handleAction(claim.id, 'approve')}
                          disabled={actionLoading === claim.id}
                        >
                          Approve
                        </button>
                        <button
                          className="claim-btn claim-btn--reject"
                          onClick={() => handleAction(claim.id, 'reject')}
                          disabled={actionLoading === claim.id}
                        >
                          Reject
                        </button>
                      </>
                    ) : (
                      <button className="claim-btn claim-btn--view">View ↗</button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Fraud thresholds legend */}
      <div className="claims-legend">
        Fraud thresholds: &lt;0.50 auto-approve · 0.50–0.75 enhanced validation · 0.75–0.90 manual review · &gt;0.90 auto-reject
      </div>
    </div>
  );
}
