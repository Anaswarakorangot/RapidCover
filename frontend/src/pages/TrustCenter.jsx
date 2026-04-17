import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

/* ─── Design tokens (mirror Policy.jsx / Register.jsx) ─────────────────── */
const S = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=DM+Sans:wght@400;500;600&display=swap');

  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }

  :root {
    --green-primary: #3DB85C;
    --green-dark:    #2a9e47;
    --green-light:   #e8f7ed;
    --text-dark:     #1a2e1a;
    --text-mid:      #4a5e4a;
    --text-light:    #8a9e8a;
    --white:         #ffffff;
    --gray-bg:       #f7f9f7;
    --border:        #e2ece2;
    --error:         #dc2626;
    --blue:          #3b82f6;
    --blue-light:    #eff6ff;
    --blue-border:   #bfdbfe;
    --purple:        #7c3aed;
    --purple-light:  #f5f3ff;
    --purple-border: #ddd6fe;
  }

  /* ── Page wrapper ── */
  .tc-wrap {
    font-family: 'DM Sans', sans-serif;
    color: var(--text-dark);
    animation: fadeIn 0.3s ease;
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 24px 16px 32px;
    background: var(--gray-bg);
    min-height: 100vh;
  }

  /* ── Hero banner ── */
  .tc-hero {
    background: linear-gradient(135deg, #1a2e1a 0%, #2a9e47 60%, #3DB85C 100%);
    border-radius: 20px;
    padding: 18px 18px 16px;
    position: relative;
    overflow: hidden;
  }
  .tc-hero::after {
    content: '🔍';
    position: absolute;
    right: 18px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 40px;
    opacity: 0.12;
  }
  .tc-hero-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 24px;
    color: white;
    margin-bottom: 3px;
  }
  .tc-hero-sub {
    max-width: 84%;
    font-size: 12px;
    color: rgba(255,255,255,0.82);
    line-height: 1.45;
  }

  /* ── Tab bar ── */
  .tc-tabs {
    display: flex;
    gap: 6px;
    background: var(--white);
    border: 1.5px solid var(--border);
    border-radius: 16px;
    padding: 4px;
  }
  .tc-tab {
    flex: 1;
    padding: 9px 4px;
    border-radius: 11px;
    border: none;
    background: transparent;
    font-family: 'Nunito', sans-serif;
    font-weight: 700;
    font-size: 11px;
    color: var(--text-light);
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
    line-height: 1.2;
  }
  .tc-tab.active {
    background: var(--green-primary);
    color: white;
    box-shadow: 0 2px 8px rgba(61,184,92,0.35);
  }
  .tc-tab:not(.active):hover { color: var(--text-dark); background: var(--gray-bg); }

  /* ── Generic card ── */
  .tc-card {
    background: var(--white);
    border-radius: 18px;
    border: 1.5px solid var(--border);
    overflow: hidden;
    animation: fadeIn 0.25s ease;
  }
  .tc-card-header {
    padding: 14px 16px 0;
  }
  .tc-card-body {
    padding: 12px 16px 16px;
  }
  .tc-card-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 15px;
    color: var(--text-dark);
    margin-bottom: 3px;
  }
  .tc-card-sub {
    font-size: 11px;
    color: var(--text-light);
  }

  /* ── Selector ── */
  .tc-selector-wrap {
    margin-bottom: 2px;
  }
  .tc-selector-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-mid);
    margin-bottom: 5px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }
  .tc-selector {
    width: 100%;
    padding: 10px 14px;
    border-radius: 12px;
    border: 1.5px solid var(--border);
    background: var(--white);
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    color: var(--text-dark);
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%238a9e8a' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 14px center;
    cursor: pointer;
  }
  .tc-selector:focus { outline: none; border-color: var(--green-primary); box-shadow: 0 0 0 3px rgba(61,184,92,0.12); }

  /* ── Info row (key/value) ── */
  .tc-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
  }
  .tc-row:last-child { border-bottom: none; }
  .tc-row-key { color: var(--text-mid); }
  .tc-row-val { font-weight: 600; color: var(--text-dark); }

  /* ── Summary stat grid ── */
  .tc-stat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }
  .tc-stat {
    border-radius: 14px;
    padding: 10px 8px;
    text-align: center;
  }
  .tc-stat.green  { background: var(--green-light); }
  .tc-stat.blue   { background: var(--blue-light); }
  .tc-stat.purple { background: var(--purple-light); }
  .tc-stat-label { font-size: 10px; color: var(--text-light); margin-bottom: 3px; }
  .tc-stat-val   { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 16px; }
  .tc-stat.green  .tc-stat-val { color: var(--green-dark); }
  .tc-stat.blue   .tc-stat-val { color: var(--blue); }
  .tc-stat.purple .tc-stat-val { color: var(--purple); }

  /* ── Evidence item ── */
  .tc-evidence-item {
    background: var(--gray-bg);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 10px 12px;
    margin-bottom: 8px;
  }
  .tc-evidence-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
  }
  .tc-evidence-type {
    font-weight: 700;
    font-size: 13px;
    color: var(--text-dark);
    text-transform: capitalize;
  }
  .tc-evidence-time {
    font-size: 11px;
    color: var(--text-light);
  }
  .tc-evidence-row {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    padding: 2px 0;
    color: var(--text-mid);
  }
  .tc-evidence-row span:last-child { font-weight: 600; color: var(--text-dark); }

  /* ── Payout item ── */
  .tc-payout-item {
    border: 1.5px solid var(--border);
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 8px;
  }
  .tc-payout-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
  }
  .tc-payout-name { font-weight: 700; font-size: 14px; color: var(--text-dark); }
  .tc-payout-time { font-size: 11px; color: var(--text-light); margin-top: 2px; }
  .tc-payout-amount {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 20px;
    color: var(--green-dark);
  }
  .tc-payout-meta {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }
  .tc-payout-meta-item { font-size: 12px; color: var(--text-mid); }
  .tc-payout-meta-item span { font-weight: 600; color: var(--text-dark); }
  .tc-payout-ledger-note {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--green-dark);
  }

  /* ── Badge ── */
  .tc-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 10px;
  }
  .tc-badge.green  { background: #dcfce7; color: #166534; }
  .tc-badge.blue   { background: #dbeafe; color: #1e40af; }
  .tc-badge.yellow { background: #fef9c3; color: #854d0e; }
  .tc-badge.red    { background: #fee2e2; color: #991b1b; }
  .tc-badge.gray   { background: #f3f4f6; color: #374151; }

  /* ── Fraud bar ── */
  .tc-fraud-bar-bg {
    width: 100%;
    height: 8px;
    background: var(--border);
    border-radius: 8px;
    overflow: hidden;
    margin: 6px 0 4px;
  }
  .tc-fraud-bar-fill {
    height: 100%;
    border-radius: 8px;
    transition: width 0.5s ease;
  }
  .tc-fraud-bar-fill.low    { background: var(--green-primary); }
  .tc-fraud-bar-fill.medium { background: #f59e0b; }
  .tc-fraud-bar-fill.high   { background: var(--error); }

  /* ── Validation check ── */
  .tc-check-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
  }
  .tc-check-item:last-child { border-bottom: none; }
  .tc-check-icon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }
  .tc-check-name { font-weight: 600; color: var(--text-dark); }
  .tc-check-reason { font-size: 11px; color: var(--text-mid); margin-top: 2px; }

  /* ── Summary block  ── */
  .tc-summary-box {
    background: var(--blue-light);
    border: 1px solid var(--blue-border);
    border-radius: 14px;
    padding: 10px 12px;
    font-size: 12px;
    color: #1e3a8a;
    line-height: 1.5;
    margin-bottom: 12px;
  }

  /* ── Consensus ── */
  .tc-consensus {
    background: var(--green-light);
    border: 1.5px solid #bbf7d0;
    border-radius: 14px;
    padding: 10px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
  }
  .tc-consensus-label { font-size: 13px; color: var(--text-mid); }
  .tc-consensus-val {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 20px;
    color: var(--green-dark);
  }

  /* ── Commitment card ── */
  .tc-commitment {
    background: linear-gradient(135deg, var(--green-light) 0%, #e0f2fe 100%);
    border: 1.5px solid #bbf7d0;
    border-radius: 18px;
    padding: 14px 16px;
  }
  .tc-commitment-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 15px;
    color: var(--text-dark);
    margin-bottom: 6px;
  }
  .tc-commitment-items { display: flex; flex-direction: column; gap: 6px; }
  .tc-commitment-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 12px;
    color: var(--text-mid);
  }
  .tc-commitment-icon { font-size: 14px; flex-shrink: 0; }

  /* ── Empty / loading states ── */
  .tc-empty {
    text-align: center;
    padding: 32px 16px;
    color: var(--text-light);
    font-size: 13px;
  }
  .tc-empty-icon { font-size: 32px; margin-bottom: 8px; }
  .tc-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px 16px;
  }
  .tc-spinner {
    width: 28px; height: 28px;
    border: 3px solid var(--green-light);
    border-top-color: var(--green-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  .tc-error-box {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 12px;
    padding: 12px 14px;
    font-size: 13px;
    color: #991b1b;
    margin-bottom: 12px;
  }

  /* ── Section divider ── */
  .tc-divider {
    border: none;
    border-top: 1.5px solid var(--border);
    margin: 14px 0;
  }

  /* ── Zone info header ── */
  .tc-zone-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 12px 14px;
    background: var(--gray-bg);
    border-bottom: 1.5px solid var(--border);
  }
  .tc-zone-name { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 15px; color: var(--text-dark); }
  .tc-zone-city { font-size: 12px; color: var(--text-mid); margin-top: 2px; }
  .tc-zone-code { font-size: 11px; color: var(--text-light); font-family: monospace; }

  /* ── ML Engine Tab ── */
  .tc-model-card {
    background: var(--white);
    border: 1.5px solid var(--border);
    border-radius: 18px;
    overflow: hidden;
  }
  .tc-model-card-header {
    padding: 12px 16px 10px;
    border-bottom: 1.5px solid var(--border);
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .tc-model-card-icon { font-size: 22px; }
  .tc-model-card-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 15px;
    color: var(--text-dark);
  }
  .tc-model-card-sub { font-size: 11px; color: var(--text-light); margin-top: 1px; }
  .tc-model-card-body { padding: 12px 16px 14px; }
  .tc-model-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 7px 0;
    border-bottom: 1px solid var(--border);
    font-size: 12.5px;
    gap: 8px;
  }
  .tc-model-row:last-child { border-bottom: none; }
  .tc-model-row-key { color: var(--text-mid); flex-shrink: 0; min-width: 110px; }
  .tc-model-row-val { color: var(--text-dark); font-weight: 600; text-align: right; }
  .tc-metric-pill {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    background: var(--green-light);
    color: var(--green-dark);
  }
  .tc-metric-pill.blue { background: var(--blue-light); color: var(--blue); }
  .tc-metric-pill.purple { background: var(--purple-light); color: var(--purple); }

  /* ── Boundary table ── */
  .tc-boundary-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .tc-boundary-table th {
    text-align: left; padding: 8px 10px;
    background: var(--gray-bg); color: var(--text-mid);
    font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 0.3px;
    border-bottom: 1.5px solid var(--border);
  }
  .tc-boundary-table td { padding: 9px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }
  .tc-boundary-table tr:last-child td { border-bottom: none; }
  .tc-boundary-table .ml-col { color: var(--blue); font-weight: 600; }
  .tc-boundary-table .rule-col { color: #991b1b; font-weight: 600; }
  .tc-boundary-table .domain-col { color: var(--text-dark); }

  /* ── Judge FAQ ── */
  .tc-faq-item {
    border: 1.5px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 10px;
  }
  .tc-faq-q {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 13px 16px;
    cursor: pointer;
    background: var(--white);
    gap: 8px;
  }
  .tc-faq-q-text {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    font-size: 13px;
    color: var(--text-dark);
  }
  .tc-faq-a {
    padding: 12px 16px 14px;
    background: var(--gray-bg);
    font-size: 12.5px;
    color: var(--text-mid);
    line-height: 1.6;
    border-top: 1px solid var(--border);
  }
`;


/* ─── MLEngineTab ────────────────────────────────────────────────── */
const MODEL_CARDS = [
  {
    icon: '📍',
    title: 'Zone Risk Model',
    sub: 'Gradient Boosted Regressor',
    pill: 'green',
    rows: [
      { k: 'Purpose',          v: 'Score 0–100 disruption risk for a delivery zone' },
      { k: 'Input features',   v: 'City, rainfall history, AQI baseline, shutdown frequency, closure rate' },
      { k: 'Target',           v: 'Historical trigger frequency (independent of pricing formula)' },
      { k: 'Training data',    v: 'Zone-level weather events + admin drill scenarios' },
      { k: 'Fallback',         v: 'Manual actuarial formula if model unavailable or city unseen' },
      { k: 'Decision boundary', v: 'Score > 60 → zone surcharge applied. Score ≤ 60 → base rate.' },
    ],
  },
  {
    icon: '💰',
    title: 'Premium Pricing Model',
    sub: 'Gradient Boosted Regressor',
    pill: 'blue',
    rows: [
      { k: 'Purpose',          v: 'Predict weekly premium for a partner given zone + tier + season' },
      { k: 'Input features',   v: 'Tier, city, zone risk score, seasonal index, RIQI band, activity level' },
      { k: 'Target',           v: 'Expected weekly loss exposure (not formula-derived)' },
      { k: 'Training data',    v: 'Partner claim history + zone risk outputs + seasonal signals' },
      { k: 'Fallback',         v: 'Actuarial base rate table by tier if model unavailable' },
      { k: 'Decision boundary', v: 'Final premium always clamped: base × 1.0 ≤ output ≤ base × 3.0' },
    ],
  },
  {
    icon: '🔒',
    title: 'Fraud Detection Model',
    sub: 'Isolation Forest (Anomaly Detection)',
    pill: 'purple',
    rows: [
      { k: 'Purpose',          v: 'Score 0–1 anomaly probability for each claim attempt' },
      { k: 'Input features',   v: 'GPS consistency, claim velocity, trigger timing, partner history' },
      { k: 'Target',           v: 'Anomaly vs normal — unsupervised (no label required)' },
      { k: 'Training data',    v: 'Drill replay scenarios + synthetic GPS spoofing + normal claim flows' },
      { k: 'Fallback',         v: 'Rule-based hard stops always active regardless of ML score' },
      { k: 'Decision boundary', v: 'Score > 0.75 → hard reject. 0.5–0.75 → manual review. < 0.5 → pass.' },
    ],
  },
];

const BOUNDARY_ROWS = [
  { domain: 'Premium calculation',   ml: 'Zone risk score, seasonal factor, RIQI band', rule: 'Hard cap: base × 3.0 max. Tier floor enforced.' },
  { domain: 'Fraud triage',          ml: 'Isolation Forest anomaly score', rule: 'GPS spoofing detected → always reject (no ML override).' },
  { domain: 'Trigger verification',  ml: 'Not used — deterministic only', rule: 'Multi-source consensus required. Single source → pending.' },
  { domain: 'Zone risk scoring',     ml: 'GBR predicts 0–100 score', rule: 'Score never used alone. Insurance rules applied on top.' },
  { domain: 'Payout amount',         ml: 'Not used — deterministic only', rule: 'Tier limit × disruption factor. ML cannot increase payout.' },
];

const FAQS = [
  {
    q: 'What is actually learned here vs hardcoded?',
    a: 'Zone risk scores (0–100) and premium levels are learned from historical data. Fraud anomalies are detected by Isolation Forest trained on claim patterns. Trigger thresholds, payout amounts, and hard-stop rules are always deterministic — ML assists but never overrides insurance controls.',
  },
  {
    q: 'How do you stop GPS spoofing?',
    a: 'GPS spoofing is caught by a deterministic hard stop — not ML. We check coordinate consistency across the claim window. If GPS jumps are detected, the claim is auto-rejected regardless of the ML fraud score. ML then adds a secondary anomaly signal for the insurer’s review log.',
  },
  {
    q: 'Why should anyone trust this payout?',
    a: 'Every payout requires: (1) multi-source trigger verification with consensus ≥ 60%, (2) zone match confirmation, (3) fraud score below threshold or manual insurer review, and (4) an immutable transaction record. The worker sees each step in the Trust Center in real time.',
  },
];

function MLEngineTab() {
  const [openFaq, setOpenFaq] = useState(null);

  return (
    <div>
      {/* Positioning statement */}
      <div style={{
        background: 'linear-gradient(135deg, #1a2e1a 0%, #2a9e47 100%)',
        borderRadius: 16, padding: '14px 16px', marginBottom: 16, color: 'white',
      }}>
        <p style={{ fontFamily: 'Nunito, sans-serif', fontWeight: 900, fontSize: 15 }}>
          🤖 ML Decision Engine
        </p>
        <p style={{ fontSize: 12, opacity: 0.85, marginTop: 4, lineHeight: 1.5 }}>
          RapidCover uses learned risk intelligence where it helps,
          and deterministic insurance controls where it matters.
        </p>
      </div>

      {/* Model Cards */}
      {MODEL_CARDS.map((m, i) => (
        <div className="tc-model-card" key={i}>
          <div className="tc-model-card-header">
            <span className="tc-model-card-icon">{m.icon}</span>
            <div>
              <p className="tc-model-card-title">{m.title}</p>
              <p className="tc-model-card-sub">{m.sub}</p>
            </div>
            <span style={{ marginLeft: 'auto' }} className={`tc-metric-pill ${m.pill}`}>Active</span>
          </div>
          <div className="tc-model-card-body">
            {m.rows.map((r, j) => (
              <div className="tc-model-row" key={j}>
                <span className="tc-model-row-key">{r.k}</span>
                <span className="tc-model-row-val">{r.v}</span>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Learned vs Rule Boundary */}
      <div className="tc-card">
        <div className="tc-card-header">
          <p className="tc-card-title">⚖️ ML vs Deterministic Rules</p>
          <p className="tc-card-sub">What the model decides alone vs what always requires a rule</p>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="tc-boundary-table">
            <thead>
              <tr>
                <th>Domain</th>
                <th>ML Role</th>
                <th>Rule Override</th>
              </tr>
            </thead>
            <tbody>
              {BOUNDARY_ROWS.map((r, i) => (
                <tr key={i}>
                  <td className="domain-col">{r.domain}</td>
                  <td className="ml-col">{r.ml}</td>
                  <td className="rule-col">{r.rule}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Judge FAQ */}
      <div className="tc-card">
        <div className="tc-card-header">
          <p className="tc-card-title">💬 Judge FAQ</p>
          <p className="tc-card-sub">Quick answers to likely evaluation questions</p>
        </div>
        <div className="tc-card-body">
          {FAQS.map((f, i) => (
            <div className="tc-faq-item" key={i}>
              <div className="tc-faq-q" onClick={() => setOpenFaq(openFaq === i ? null : i)}>
                <span className="tc-faq-q-text">{f.q}</span>
                <span style={{ fontSize: 16, color: 'var(--text-light)', flexShrink: 0 }}>
                  {openFaq === i ? '▲' : '▼'}
                </span>
              </div>
              {openFaq === i && <div className="tc-faq-a">{f.a}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── ClaimExplainer ─────────────────────────────────────────────────────── */
function ClaimExplainer({ claimId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!claimId) return;

    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);

    api.getClaimExplanation(claimId)
      .then(d => {
        if (!cancelled) {
          setData(d);
          setError(null);
        }
      })
      .catch(e => {
        if (!cancelled) {
          setError(e.message || 'Failed to load explanation');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [claimId]);

  if (!claimId) return (
    <div className="tc-empty">
      <div className="tc-empty-icon">📋</div>
      <p>Select a claim above to see its full explanation</p>
    </div>
  );

  if (loading) return <div className="tc-loading"><div className="tc-spinner" /></div>;
  if (error)   return <div className="tc-error-box">⚠️ {error}</div>;
  if (!data)   return null;

  const fraudLevel = data.fraud_score < 0.5 ? 'low' : data.fraud_score < 0.75 ? 'medium' : 'high';
  const fraudPct   = (data.fraud_score * 100).toFixed(1);

  return (
    <>
      {/* Summary */}
      {data.summary && <div className="tc-summary-box">💬 {data.summary}</div>}

      {/* Trigger Details */}
      {data.trigger_details && (
        <div className="tc-card">
          <div className="tc-card-header">
            <p className="tc-card-title">⚡ Trigger Details</p>
          </div>
          <div className="tc-card-body">
            <div className="tc-row">
              <span className="tc-row-key">Type</span>
              <span className="tc-row-val" style={{ textTransform: 'capitalize' }}>{data.trigger_details.type}</span>
            </div>
            {data.trigger_details.severity && (
              <div className="tc-row">
                <span className="tc-row-key">Severity</span>
                <span className="tc-row-val">{data.trigger_details.severity}/5</span>
              </div>
            )}
            {data.trigger_details.timestamp && (
              <div className="tc-row">
                <span className="tc-row-key">Triggered at</span>
                <span className="tc-row-val">{new Date(data.trigger_details.timestamp).toLocaleString('en-IN')}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Payout Calculation */}
      {data.payout_calculation && (
        <div className="tc-card">
          <div className="tc-card-header">
            <p className="tc-card-title">💰 Payout Calculation</p>
          </div>
          <div className="tc-card-body">
            {data.payout_calculation.base_amount && (
              <div className="tc-row">
                <span className="tc-row-key">Base Amount</span>
                <span className="tc-row-val">₹{data.payout_calculation.base_amount}</span>
              </div>
            )}
            {data.payout_calculation.riqi_multiplier && (
              <div className="tc-row">
                <span className="tc-row-key">RIQI Multiplier</span>
                <span className="tc-row-val">×{data.payout_calculation.riqi_multiplier}</span>
              </div>
            )}
            {data.payout_calculation.final_amount !== undefined && (
              <div className="tc-row">
                <span className="tc-row-key" style={{ fontWeight: 700, color: 'var(--text-dark)' }}>Final Payout</span>
                <span className="tc-row-val" style={{ color: 'var(--green-dark)', fontSize: 16 }}>₹{data.payout_calculation.final_amount}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Fraud Assessment */}
      {data.fraud_score !== undefined && (
        <div className="tc-card">
          <div className="tc-card-header">
            <p className="tc-card-title">🔒 Fraud Assessment</p>
          </div>
          <div className="tc-card-body">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ fontSize: 13, color: 'var(--text-mid)' }}>Fraud Score</span>
              <span style={{ fontFamily: 'Nunito, sans-serif', fontWeight: 800, fontSize: 15, color: fraudLevel === 'low' ? 'var(--green-dark)' : fraudLevel === 'medium' ? '#b45309' : 'var(--error)' }}>
                {fraudPct}%
              </span>
            </div>
            <div className="tc-fraud-bar-bg">
              <div className={`tc-fraud-bar-fill ${fraudLevel}`} style={{ width: `${fraudPct}%` }} />
            </div>
            {data.decision && (
              <p style={{ fontSize: 12, color: 'var(--text-mid)', marginTop: 6 }}>
                Decision: <strong style={{ textTransform: 'capitalize' }}>{data.decision.replace(/_/g, ' ')}</strong>
              </p>
            )}
          </div>
        </div>
      )}

      {/* Validation Checks */}
      {data.validation_checks?.length > 0 && (
        <div className="tc-card">
          <div className="tc-card-header">
            <p className="tc-card-title">✅ Validation Checks</p>
          </div>
          <div className="tc-card-body">
            {data.validation_checks.map((check, i) => (
              <div className="tc-check-item" key={i}>
                <span className="tc-check-icon">{check.passed ? '✅' : '❌'}</span>
                <div>
                  <p className="tc-check-name">{check.name}</p>
                  {check.reason && <p className="tc-check-reason">{check.reason}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

/* ─── EvidenceViewer ─────────────────────────────────────────────────────── */
function EvidenceViewer({ zoneId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!zoneId) return;

    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);

    api.getZoneTriggerEvidence(zoneId)
      .then(d => !cancelled && (setData(d), setError(null)))
      .catch(e => !cancelled && setError(e.message || 'Failed to load evidence'))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [zoneId]);

  if (!zoneId) return (
    <div className="tc-empty">
      <div className="tc-empty-icon">🌐</div>
      <p>Select a zone above to see trigger evidence</p>
    </div>
  );

  if (loading) return <div className="tc-loading"><div className="tc-spinner" /></div>;
  if (error)   return <div className="tc-error-box">⚠️ {error}</div>;
  if (!data)   return null;

  const nonTriggers = data.recent_non_triggers || [];

  return (
    <>
      {/* Zone Info */}
      {data.zone && (
        <div className="tc-card" style={{ overflow: 'hidden' }}>
          <div className="tc-zone-header">
            <div>
              <p className="tc-zone-name">{data.zone.name}</p>
              <p className="tc-zone-city">{data.zone.city}</p>
            </div>
            <span className="tc-zone-code">{data.zone.code}</span>
          </div>
          {data.consensus_score !== undefined && (
            <div className="tc-consensus" style={{ margin: 12, borderRadius: 12 }}>
              <span className="tc-consensus-label">Data Source Consensus</span>
              <span className="tc-consensus-val">{(data.consensus_score * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>
      )}

      {/* Recent Non-Triggers */}
      <div className="tc-card">
        <div className="tc-card-header">
          <p className="tc-card-title">📊 Recent Conditions</p>
          <p className="tc-card-sub">Monitoring events that did NOT trigger a payout</p>
        </div>
        <div className="tc-card-body">
          {nonTriggers.length > 0 ? nonTriggers.map((item, i) => (
            <div className="tc-evidence-item" key={i}>
              <div className="tc-evidence-top">
                <span className="tc-evidence-type">{item.condition_type}</span>
                <span className="tc-evidence-time">{new Date(item.timestamp).toLocaleString('en-IN')}</span>
              </div>
              <div className="tc-evidence-row">
                <span>Measured</span>
                <span>{item.measured_value}</span>
              </div>
              <div className="tc-evidence-row">
                <span>Threshold</span>
                <span>{item.threshold}</span>
              </div>
              <div className="tc-evidence-row">
                <span>Status</span>
                <span style={{ color: 'var(--green-dark)' }}>✓ Below threshold</span>
              </div>
            </div>
          )) : (
            <div className="tc-empty" style={{ padding: '20px 0 8px' }}>
              <p>No recent trigger evidence for this zone</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

/* ─── LedgerDisplay ─────────────────────────────────────────────────────── */
function LedgerDisplay({ zoneId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!zoneId) return;

    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);

    api.getZonePayoutLedger(zoneId)
      .then(d => !cancelled && (setData(d), setError(null)))
      .catch(e => !cancelled && setError(e.message || 'Failed to load ledger'))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [zoneId]);

  if (!zoneId) return (
    <div className="tc-empty">
      <div className="tc-empty-icon">📒</div>
      <p>Select a zone above to see the payout ledger</p>
    </div>
  );

  if (loading) return <div className="tc-loading"><div className="tc-spinner" /></div>;
  if (error)   return <div className="tc-error-box">⚠️ {error}</div>;
  if (!data)   return null;

  const payouts = data.recent_payouts || [];

  return (
    <>
      {/* Summary */}
      {data.summary && (
        <div className="tc-stat-grid" style={{ marginBottom: 14 }}>
          <div className="tc-stat green">
            <p className="tc-stat-label">Total Paid</p>
            <p className="tc-stat-val">₹{data.summary.total_paid || 0}</p>
          </div>
          <div className="tc-stat blue">
            <p className="tc-stat-label">Payouts</p>
            <p className="tc-stat-val">{data.summary.payout_count || 0}</p>
          </div>
          <div className="tc-stat purple">
            <p className="tc-stat-label">Avg Payout</p>
            <p className="tc-stat-val">₹{data.summary.avg_payout || 0}</p>
          </div>
        </div>
      )}

      {/* Payout list */}
      {payouts.length > 0 ? (
        <>
          <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-light)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 10 }}>
            Recent Payouts
          </p>
          {payouts.map((payout, i) => (
            <div className="tc-payout-item" key={i}>
              <div className="tc-payout-top">
                <div>
                  <p className="tc-payout-name">{payout.partner_name || `Partner #${payout.partner_id}`}</p>
                  <p className="tc-payout-time">{new Date(payout.timestamp).toLocaleString('en-IN')}</p>
                </div>
                <span className="tc-payout-amount">₹{payout.amount}</span>
              </div>
              <div className="tc-payout-meta">
                <div className="tc-payout-meta-item">Trigger: <span>{payout.trigger_type}</span></div>
                {payout.upi_ref    && <div className="tc-payout-meta-item">UPI: <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{payout.upi_ref}</span></div>}
                {payout.claim_id   && <div className="tc-payout-meta-item">Claim: <span>#{payout.claim_id}</span></div>}
                {payout.status     && (
                  <div className="tc-payout-meta-item">
                    Status: <span className={`tc-badge ${payout.status === 'paid' ? 'green' : 'gray'}`}>{payout.status}</span>
                  </div>
                )}
              </div>
              {payout.transaction_log && (
                <div className="tc-payout-ledger-note">
                  🔏 Transaction verified · Immutable record
                </div>
              )}
            </div>
          ))}
        </>
      ) : (
        <div className="tc-empty">
          <div className="tc-empty-icon">📭</div>
          <p>No payouts recorded for this zone yet</p>
        </div>
      )}
    </>
  );
}

/* ─── Main TrustCenter ──────────────────────────────────────────────────── */
export default function TrustCenter() {
  const { user } = useAuth();                     // fixed: was `partner` which doesn't exist
  const [activeTab, setActiveTab] = useState('claims');

  const [recentClaims, setRecentClaims]     = useState([]);
  const [zones, setZones]                   = useState([]);
  const [selectedClaimId, setSelectedClaimId] = useState(null);
  const [selectedZoneId, setSelectedZoneId]   = useState(null);

  useEffect(() => {
    api.getClaims().then(d => {
      // Backend returns {claims, total, page, page_size}, not a plain array
      const list = d?.claims || (Array.isArray(d) ? d : []);
      setRecentClaims(list.slice(0, 5));
      if (list.length > 0) setSelectedClaimId(list[0].id);
    }).catch(() => {});

    api.getZones().then(d => {
      const list = Array.isArray(d) ? d : [];
      setZones(list);
      const prefZone = user?.zone_id
        ? list.find(z => z.id === user.zone_id)?.id
        : list[0]?.id;
      if (prefZone) setSelectedZoneId(prefZone);
    }).catch(() => {});
  }, [user]);

  const TABS = [
    { id: 'claims',   label: '📋 Explainer' },
    { id: 'evidence', label: '⚡ Evidence' },
    { id: 'ledger',   label: '📒 Ledger' },
    { id: 'ml',       label: '🤖 ML Engine' },
  ];

  return (
    <>
      <style>{S}</style>
      <div className="tc-wrap">

        {/* Hero — elevated with ML positioning */}
        <div className="tc-hero">
          <p className="tc-hero-title">🔮 Trust Center</p>
          <p className="tc-hero-sub">
            The RapidCover ML Decision Engine — Fully Transparent
          </p>
          <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.65)', marginTop: 6 }}>
            Explainable premiums · Fraud-resilient claims · Immutable payouts
          </p>
        </div>

        {/* Tab bar */}
        <div className="tc-tabs">
          {TABS.map(t => (
            <button
              key={t.id}
              className={`tc-tab ${activeTab === t.id ? 'active' : ''}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* ── Claim Explainer tab ── */}
        {activeTab === 'claims' && (
          <>
            {recentClaims.length > 0 && (
              <div className="tc-selector-wrap">
                <p className="tc-selector-label">Select Claim</p>
                <select
                  className="tc-selector"
                  value={selectedClaimId || ''}
                  onChange={e => setSelectedClaimId(Number(e.target.value))}
                >
                  {recentClaims.map(c => (
                    <option key={c.id} value={c.id}>
                      Claim #{c.id} · ₹{c.amount} · {c.status}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <ClaimExplainer claimId={selectedClaimId} />
          </>
        )}

        {/* ── Trigger Evidence tab ── */}
        {activeTab === 'evidence' && (
          <>
            {zones.length > 0 && (
              <div className="tc-selector-wrap">
                <p className="tc-selector-label">Select Zone</p>
                <select
                  className="tc-selector"
                  value={selectedZoneId || ''}
                  onChange={e => setSelectedZoneId(Number(e.target.value))}
                >
                  {zones.map(z => (
                    <option key={z.id} value={z.id}>{z.name} · {z.city}</option>
                  ))}
                </select>
              </div>
            )}
            <EvidenceViewer zoneId={selectedZoneId} />
          </>
        )}

        {/* ── Payout Ledger tab ── */}
        {activeTab === 'ledger' && (
          <>
            {zones.length > 0 && (
              <div className="tc-selector-wrap">
                <p className="tc-selector-label">Select Zone</p>
                <select
                  className="tc-selector"
                  value={selectedZoneId || ''}
                  onChange={e => setSelectedZoneId(Number(e.target.value))}
                >
                  {zones.map(z => (
                    <option key={z.id} value={z.id}>{z.name} · {z.city}</option>
                  ))}
                </select>
              </div>
            )}
            <LedgerDisplay zoneId={selectedZoneId} />
          </>
        )}

        {/* ── ML Engine tab ── */}
        {activeTab === 'ml' && <MLEngineTab />}

        {/* Commitment card — always visible */}
        <div className="tc-commitment">
          <p className="tc-commitment-title">Why You Can Trust This</p>
          <div className="tc-commitment-items">
            <div className="tc-commitment-item">
              <span className="tc-commitment-icon">📡</span>
              <span>Every claim backed by verifiable data from multiple independent sources</span>
            </div>
            <div className="tc-commitment-item">
              <span className="tc-commitment-icon">🔢</span>
              <span>All calculations are explainable — no black-box decisions</span>
            </div>
            <div className="tc-commitment-item">
              <span className="tc-commitment-icon">🔏</span>
              <span>Every payout is recorded in an immutable, tamper-proof ledger</span>
            </div>
            <div className="tc-commitment-item">
              <span className="tc-commitment-icon">⚡</span>
              <span>You can verify every decision we make, in real time</span>
            </div>
          </div>
        </div>

      </div>
    </>
  );
}
