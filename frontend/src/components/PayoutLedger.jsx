/**
 * PayoutLedger.jsx  –  Trust building recent payout data for a zone
 * 
 * Shows a scrolling list of recent payouts and key trust metrics.
 */

import { useState, useEffect } from 'react';
import api from '../services/api';

const S = `
  .ledger-wrap {
    background: #ffffff;
    border: 1.5px solid #e2ece2;
    border-radius: 20px;
    padding: 18px;
    margin-top: 16px;
    font-family: 'DM Sans', sans-serif;
  }
  .ledger-header { margin-bottom: 16px; }
  .ledger-title  { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 15px; color: #1a2e1a; }
  .ledger-sub    { font-size: 11px; color: #8a9e8a; margin-top: 2px; }
  
  .ledger-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
    padding: 12px;
    background: #f7f9f7;
    border-radius: 14px;
  }
  .l-stat-lbl { font-size: 10px; color: #4a5e4a; text-transform: uppercase; letter-spacing: 0.5px; }
  .l-stat-val { font-family: 'Nunito', sans-serif; font-size: 16px; font-weight: 900; color: #3DB85C; margin-top: 2px; }

  .ledger-table { width: 100%; border-collapse: collapse; }
  .ledger-row   { border-bottom: 1px solid #f3f4f6; }
  .ledger-row:last-child { border-bottom: none; }
  .ledger-cell  { padding: 10px 0; font-size: 12px; }
  .l-amt { font-weight: 700; color: #1a2e1a; }
  .l-time { color: #8a9e8a; font-size: 11px; text-align: right; }
  .l-speed { color: #2a9e47; font-weight: 600; font-size: 11px; text-align: right; }

  .disclosure {
    font-size: 10px;
    color: #8a9e8a;
    margin-top: 12px;
    line-height: 1.4;
    font-style: italic;
  }
`;

export default function PayoutLedger({ zoneId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (zoneId) {
      api.getZonePayoutLedger(zoneId)
        .then(setData)
        .catch(err => console.error("Failed to fetch ledger:", err))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [zoneId]);

  if (loading) return <div style={{ padding: 20, textAlign: 'center', fontSize: 12, color: '#8a9e8a' }}>Verifying trust ledger...</div>;
  if (!data) return null;

  return (
    <>
      <style>{S}</style>
      <div className="ledger-wrap">
        <div className="ledger-header">
          <p className="ledger-title">Payout Proof Ledger</p>
          <p className="ledger-sub">Live verification from your current zone</p>
        </div>

        <div className="ledger-stats">
          <div>
            <p className="l-stat-lbl">Median Speed</p>
            <p className="l-stat-val">{data.median_payout_time_mins || 0} mins</p>
          </div>
          <div>
            <p className="l-stat-lbl">Paid this Week</p>
            <p className="l-stat-val">₹{(data.total_paid_this_week || 0).toLocaleString()}</p>
          </div>
        </div>

        <table className="ledger-table">
          <tbody>
            {(data.recent_payouts || []).map((p, i) => (
              <tr key={i} className="ledger-row">
                <td className="ledger-cell l-amt">₹{p.amount}</td>
                <td className="ledger-cell l-time">{new Date(p.paid_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                <td className="ledger-cell l-speed">+{p.payout_time_mins}m settle</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p className="disclosure">
          Transparency Note: RapidCover maintains a {(data.miss_rate_disclosure * 100).toFixed(1)}% claim rejection rate for fraud prevention. 
          All settlements above are cryptographically signed.
        </p>
      </div>
    </>
  );
}
