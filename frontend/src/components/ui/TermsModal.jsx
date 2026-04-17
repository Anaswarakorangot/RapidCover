import React from 'react';
// src/components/ui/TermsModal.jsx
// Drop this file into frontend/src/components/ui/

const termsStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=DM+Sans:wght@400;500;600&display=swap');

  .tm-overlay {
    position: fixed;
    inset: 0;
    background: rgba(10, 20, 10, 0.72);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    z-index: 1000;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    animation: tm-fade-in 0.2s ease;
  }

  @keyframes tm-fade-in {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  .tm-sheet {
    width: 100%;
    max-width: 480px;
    max-height: 92vh;
    background: #ffffff;
    border-radius: 28px 28px 0 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    animation: tm-slide-up 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    box-shadow: 0 -12px 60px rgba(0,0,0,0.18);
  }

  @keyframes tm-slide-up {
    from { transform: translateY(100%); opacity: 0.6; }
    to   { transform: translateY(0);   opacity: 1; }
  }

  .tm-header {
    padding: 20px 24px 16px;
    border-bottom: 1.5px solid #e8f0e8;
    flex-shrink: 0;
  }

  .tm-pill {
    width: 40px;
    height: 4px;
    background: #d0ddd0;
    border-radius: 4px;
    margin: 0 auto 16px;
  }

  .tm-header-top {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 6px;
  }

  .tm-icon {
    width: 44px;
    height: 44px;
    background: #3DB85C;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(61,184,92,0.3);
  }

  .tm-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 20px;
    color: #1a2e1a;
    line-height: 1.2;
  }

  .tm-subtitle {
    font-size: 12.5px;
    color: #6a8a6a;
    margin-top: 2px;
    font-family: 'DM Sans', sans-serif;
  }

  .tm-progress-bar {
    height: 3px;
    background: #e8f0e8;
    border-radius: 4px;
    margin-top: 14px;
    overflow: hidden;
  }

  .tm-progress-fill {
    height: 100%;
    background: #3DB85C;
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .tm-progress-label {
    font-size: 11px;
    color: #8a9e8a;
    margin-top: 5px;
    font-family: 'DM Sans', sans-serif;
    text-align: right;
  }

  /* ── Scroll body ── */
  .tm-body {
    overflow-y: auto;
    flex: 1;
    padding: 20px 20px 8px;
    scroll-behavior: smooth;
  }

  .tm-body::-webkit-scrollbar { width: 4px; }
  .tm-body::-webkit-scrollbar-track { background: transparent; }
  .tm-body::-webkit-scrollbar-thumb { background: #c8dcc8; border-radius: 4px; }

  /* ── Sections ── */
  .tm-section {
    margin-bottom: 22px;
  }

  .tm-section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
  }

  .tm-section-icon {
    width: 34px;
    height: 34px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
  }

  .tm-section-icon.green  { background: #e8f7ed; }
  .tm-section-icon.red    { background: #fef2f2; }
  .tm-section-icon.amber  { background: #fef8e7; }
  .tm-section-icon.blue   { background: #eff6ff; }

  .tm-section-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    font-size: 15px;
    color: #1a2e1a;
  }

  /* ── Trigger cards (what's covered) ── */
  .tm-trigger-grid {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .tm-trigger-card {
    background: #f3fbf5;
    border: 1.5px solid #c8e8d0;
    border-radius: 14px;
    padding: 12px 14px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .tm-trigger-emoji {
    font-size: 20px;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .tm-trigger-info {}

  .tm-trigger-name {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    font-size: 13.5px;
    color: #1a4a1a;
    margin-bottom: 2px;
  }

  .tm-trigger-desc {
    font-size: 12px;
    color: #4a6e4a;
    line-height: 1.4;
  }

  .tm-trigger-threshold {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #3DB85C;
    color: #fff;
    font-size: 10.5px;
    font-family: 'Nunito', sans-serif;
    font-weight: 700;
    border-radius: 6px;
    padding: 2px 7px;
    margin-top: 5px;
  }

  /* ── Exclusion list ── */
  .tm-exclusion-list {
    display: flex;
    flex-direction: column;
    gap: 7px;
  }

  .tm-exclusion-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    background: #fff5f5;
    border: 1.5px solid #fecaca;
    border-radius: 12px;
    padding: 10px 12px;
  }

  .tm-excl-x {
    width: 20px;
    height: 20px;
    background: #fee2e2;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    color: #dc2626;
    font-weight: 900;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .tm-excl-text {
    font-size: 12.5px;
    color: #7f1d1d;
    line-height: 1.4;
  }

  .tm-excl-text strong {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    display: block;
    font-size: 13px;
    color: #991b1b;
    margin-bottom: 1px;
  }

  /* ── Payout timeline ── */
  .tm-payout-box {
    background: linear-gradient(135deg, #f0fbf4, #e8f7ed);
    border: 1.5px solid #a8d8b8;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 22px;
  }

  .tm-payout-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 14px;
    color: #1a4a1a;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .tm-payout-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid #c8e8d0;
    font-size: 12.5px;
  }

  .tm-payout-row:last-child { border-bottom: none; }

  .tm-payout-key { color: #4a6e4a; }

  .tm-payout-val {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    color: #1a4a1a;
  }

  .tm-payout-val.green { color: #3DB85C; }

  /* ── Key terms ── */
  .tm-key-terms {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .tm-term-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px 12px;
    background: #f7f9f7;
    border-radius: 12px;
    border: 1.5px solid #e2ece2;
  }

  .tm-term-dot {
    width: 7px;
    height: 7px;
    background: #3DB85C;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 5px;
  }

  .tm-term-text {
    font-size: 12.5px;
    color: #3a4e3a;
    line-height: 1.45;
  }

  .tm-term-text strong {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    color: #1a2e1a;
  }

  /* ── Divider ── */
  .tm-divider {
    height: 1px;
    background: #e8f0e8;
    margin: 4px 0 22px;
  }

  /* ── Footer ── */
  .tm-footer {
    padding: 14px 20px 24px;
    border-top: 1.5px solid #e8f0e8;
    background: #fff;
    flex-shrink: 0;
  }

  .tm-scroll-hint {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    font-size: 12px;
    color: #8a9e8a;
    margin-bottom: 14px;
    font-family: 'DM Sans', sans-serif;
    transition: opacity 0.3s;
  }

  .tm-scroll-hint.hidden { opacity: 0; pointer-events: none; }

  .tm-checkbox-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 14px;
    padding: 12px 14px;
    background: #f3fbf5;
    border-radius: 14px;
    border: 1.5px solid #b6dfc0;
    cursor: pointer;
    transition: background 0.2s, border-color 0.2s;
  }

  .tm-checkbox-row:hover { background: #e8f7ed; }
  .tm-checkbox-row.checked { border-color: #3DB85C; background: #e8f7ed; }

  .tm-checkbox {
    width: 22px;
    height: 22px;
    border-radius: 7px;
    border: 2px solid #b6dfc0;
    background: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.2s;
    margin-top: 1px;
  }

  .tm-checkbox.checked {
    background: #3DB85C;
    border-color: #3DB85C;
  }

  .tm-checkbox-label {
    font-size: 13px;
    color: #2a4a2a;
    line-height: 1.45;
    font-family: 'DM Sans', sans-serif;
  }

  .tm-checkbox-label strong {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    color: #1a2e1a;
  }

  .tm-accept-btn {
    width: 100%;
    padding: 16px;
    background: #3DB85C;
    border: none;
    border-radius: 16px;
    color: #fff;
    font-family: 'Nunito', sans-serif;
    font-size: 16px;
    font-weight: 900;
    cursor: pointer;
    transition: opacity 0.2s, transform 0.15s;
    box-shadow: 0 6px 20px rgba(61,184,92,0.35);
    position: relative;
    overflow: hidden;
  }

  .tm-accept-btn::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.15) 0%, transparent 55%);
    pointer-events: none;
  }

  .tm-accept-btn:disabled {
    background: #c8d8c8;
    box-shadow: none;
    cursor: not-allowed;
  }

  .tm-accept-btn:not(:disabled):active { transform: scale(0.97); }

  .tm-decline-btn {
    width: 100%;
    padding: 10px;
    background: transparent;
    border: none;
    color: #8a9e8a;
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    margin-top: 8px;
    text-decoration: underline;
    text-underline-offset: 3px;
  }
`;

const TRIGGERS = [
  {
    emoji: '🌧️',
    name: 'Heavy Rain / Flash Flood',
    desc: 'Rainfall > 55mm/hr for 30+ mins in your dark store pin code, or IMD orange/red alert issued.',
    threshold: 'Auto-payout in ~8 mins',
  },
  {
    emoji: '🌡️',
    name: 'Extreme Heat Advisory',
    desc: 'Temperature > 43°C sustained 4+ hours, or state govt issues outdoor work restriction.',
    threshold: 'Full disruption window paid',
  },
  {
    emoji: '🌫️',
    name: 'Dangerous AQI (Air Quality)',
    desc: 'AQI > 400 (Severe) in your zone for 3+ hours, or govt issues outdoor restriction.',
    threshold: 'Hours of breach × hourly rate',
  },
  {
    emoji: '🚫',
    name: 'Civic Shutdown / Curfew / Bandh',
    desc: 'Official curfew, Section 144, or bandh in your delivery zone for 2+ hours.',
    threshold: 'Full income for shutdown duration',
  },
  {
    emoji: '🏪',
    name: 'Dark Store Force Closure',
    desc: 'Your assigned dark store closes > 90 mins due to an external event (not maintenance).',
    threshold: 'Full shift income covered',
  },
];

const EXCLUSIONS = [
  { title: 'War & Armed Conflict', detail: 'Any income loss from war, civil war, armed insurgency, or terrorism.' },
  { title: 'Pandemic / Epidemic', detail: 'National/state declared health emergencies like COVID-type lockdowns.' },
  { title: 'Nuclear Events', detail: 'Any disruption from nuclear reaction, radiation, or radioactive contamination.' },
  { title: 'Platform Policy Changes', detail: 'Commission changes, algorithm updates, surge removal, or voluntary platform shutdowns.' },
  { title: 'Planned Maintenance', detail: 'Scheduled store downtimes or maintenance-related closures.' },
  { title: 'Self-Inflicted Loss', detail: 'Going offline voluntarily, account suspensions from violations, or avoiding runs.' },
  { title: 'Health, Accident & Life', detail: 'Medical expenses, hospitalisation, disability, or death — strictly not covered.' },
  { title: 'Vehicle Damage', detail: 'Bike damage, repair costs, fuel costs — not covered.' },
  { title: 'Under 45 Minutes', detail: 'Events resolving within 45 minutes do not qualify for a payout.' },
  { title: 'Claims After 48 Hours', detail: 'Claims submitted more than 48 hours after the disruption window closes.' },
  { title: 'Indirect / Consequential Loss', detail: 'Loss beyond the verified income window — tips, future projections, reputation.' },
];

const KEY_TERMS = [
  { text: <><strong>Parametric insurance</strong> — Payout is triggered automatically by verified data, not by you filing a claim. You do nothing.</> },
  { text: <><strong>Zero-touch claims</strong> — Trigger detected → validated → UPI credit in ~8 minutes. No forms, no calls, no waiting.</> },
  { text: <><strong>Weekly renewal</strong> — Coverage auto-renews every Monday 6 AM via UPI auto-debit. 3-day grace period on missed payment.</> },
  { text: <><strong>Minimum disruption threshold</strong> — Events under 45 minutes are excluded to prevent micro-claim abuse.</> },
  { text: <><strong>GPS coherence check</strong> — Your location must match your declared dark store zone during the disruption window.</> },
  { text: <><strong>Fraud detection</strong> — ML fraud score computed per claim. Score above 0.90 = auto-reject with explanation sent to you.</> },
  { text: <><strong>Catastrophe cap</strong> — In rare city-wide events, payouts may be proportionally reduced if total claims exceed the city's weekly premium pool.</> },
  { text: <><strong>Aadhaar-linked policy</strong> — Your policy is tied to your identity, not just your platform account. One policy per person.</> },
];

export function TermsModal({ onAccept, onDecline }) {
  const [checked, setChecked] = React.useState(false);
  const [scrollProgress, setScrollProgress] = React.useState(0);
  const [hasScrolledToBottom, setHasScrolledToBottom] = React.useState(false);
  const bodyRef = React.useRef(null);

  function handleScroll() {
    const el = bodyRef.current;
    if (!el) return;
    const progress = el.scrollTop / (el.scrollHeight - el.clientHeight);
    setScrollProgress(Math.min(progress * 100, 100));
    if (progress > 0.99) setHasScrolledToBottom(true);
  }

  return (
    <>
      <style>{termsStyles}</style>
      <div className="tm-overlay">
        <div className="tm-sheet">

          {/* Header */}
          <div className="tm-header">
            <div className="tm-pill" />
            <div className="tm-header-top">
              <div className="tm-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <path d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
                    stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div>
                <div className="tm-title">Terms & Coverage</div>
                <div className="tm-subtitle">Read before activating your account</div>
              </div>
            </div>
            <div className="tm-progress-bar">
              <div className="tm-progress-fill" style={{ width: `${scrollProgress}%` }} />
            </div>
            <div className="tm-progress-label">{Math.round(scrollProgress)}% read</div>
          </div>

          {/* Scrollable Body */}
          <div className="tm-body" ref={bodyRef} onScroll={handleScroll}>

            {/* Payout summary box */}
            <div className="tm-payout-box">
              <div className="tm-payout-title">⚡ How RapidCover Works</div>
              <div className="tm-payout-row">
                <span className="tm-payout-key">Trigger to payout</span>
                <span className="tm-payout-val green">~8 minutes</span>
              </div>
              <div className="tm-payout-row">
                <span className="tm-payout-key">Action needed from you</span>
                <span className="tm-payout-val green">Zero</span>
              </div>
              <div className="tm-payout-row">
                <span className="tm-payout-key">Weekly premium (Standard)</span>
                <span className="tm-payout-val">₹59 / week</span>
              </div>
              <div className="tm-payout-row">
                <span className="tm-payout-key">Max payout / day</span>
                <span className="tm-payout-val">₹350 – ₹900</span>
              </div>
              <div className="tm-payout-row">
                <span className="tm-payout-key">Payout method</span>
                <span className="tm-payout-val">UPI direct credit</span>
              </div>
            </div>

            {/* What's Covered */}
            <div className="tm-section">
              <div className="tm-section-header">
                <div className="tm-section-icon green">✅</div>
                <div className="tm-section-title">What's Covered — 5 Triggers</div>
              </div>
              <div className="tm-trigger-grid">
                {TRIGGERS.map((t, i) => (
                  <div className="tm-trigger-card" key={i}>
                    <div className="tm-trigger-emoji">{t.emoji}</div>
                    <div className="tm-trigger-info">
                      <div className="tm-trigger-name">{t.name}</div>
                      <div className="tm-trigger-desc">{t.desc}</div>
                      <div className="tm-trigger-threshold">⚡ {t.threshold}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="tm-divider" />

            {/* What's NOT Covered */}
            <div className="tm-section">
              <div className="tm-section-header">
                <div className="tm-section-icon red">🚫</div>
                <div className="tm-section-title">What's NOT Covered</div>
              </div>
              <div className="tm-exclusion-list">
                {EXCLUSIONS.map((e, i) => (
                  <div className="tm-exclusion-item" key={i}>
                    <div className="tm-excl-x">✕</div>
                    <div className="tm-excl-text">
                      <strong>{e.title}</strong>
                      {e.detail}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="tm-divider" />

            {/* Key Terms */}
            <div className="tm-section">
              <div className="tm-section-header">
                <div className="tm-section-icon blue">📋</div>
                <div className="tm-section-title">Key Terms You Should Know</div>
              </div>
              <div className="tm-key-terms">
                {KEY_TERMS.map((t, i) => (
                  <div className="tm-term-item" key={i}>
                    <div className="tm-term-dot" />
                    <div className="tm-term-text">{t.text}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="tm-divider" />



            {/* Bottom spacer */}
            <div style={{ height: 16 }} />
          </div>

          {/* Footer */}
          <div className="tm-footer">
            <div className={`tm-scroll-hint${hasScrolledToBottom ? ' hidden' : ''}`}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M12 5v14M5 12l7 7 7-7" stroke="#8a9e8a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Scroll to read all terms
            </div>

            <div
              className={`tm-checkbox-row${checked ? ' checked' : ''}`}
              onClick={() => {
                if (hasScrolledToBottom) {
                  setChecked(c => !c);
                }
              }}
              style={{
                opacity: hasScrolledToBottom ? 1 : 0.5,
                cursor: hasScrolledToBottom ? 'pointer' : 'not-allowed'
              }}
            >
              <div className={`tm-checkbox${checked ? ' checked' : ''}`}>
                {checked && (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </div>
              <div className="tm-checkbox-label">
                <strong>I have read and understood the terms.</strong> I know what RapidCover covers and what it does not cover.
              </div>
            </div>

            <button
              className="tm-accept-btn"
              disabled={!checked}
              onClick={onAccept}
            >
              {checked ? '✓ Activate My Account' : 'Tick the box above to proceed'}
            </button>

            <button className="tm-decline-btn" onClick={onDecline}>
              Cancel registration
            </button>
          </div>

        </div>
      </div>
    </>
  );
}
