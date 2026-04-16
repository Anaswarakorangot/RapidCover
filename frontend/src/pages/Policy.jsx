import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../services/api';
import PayoutLedger from '../components/PayoutLedger';
import { useAuth } from '../context/AuthContext';

/* ─── Design tokens matching Register.jsx ───────────────────────────────── */
const S = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=DM+Sans:wght@400;500;600&display=swap');

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
    --warning:       #d97706;
    --error:         #dc2626;
  }

  .pol-wrap {
    font-family: 'DM Sans', sans-serif;
    color: var(--text-dark);
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-bottom: 32px;
  }

  /* ── Page header ── */
  .pol-page-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 24px;
    color: var(--text-dark);
  }
  .pol-page-sub { font-size: 13px; color: var(--text-light); margin-top: 2px; }

  /* ── Card ── */
  .pol-card {
    background: var(--white);
    border-radius: 20px;
    border: 1.5px solid var(--border);
    overflow: hidden;
  }
  .pol-card.ring-active { border-color: var(--green-primary); box-shadow: 0 0 0 3px rgba(61,184,92,0.15); }
  .pol-card.locked { opacity: 0.55; }

  .pol-card-body    { padding: 18px 18px 14px; }
  .pol-card-footer  { padding: 0 18px 16px; }

  /* ── Plan card header ── */
  .plan-hdr { display: flex; justify-content: space-between; align-items: flex-start; }
  .plan-icon { font-size: 28px; }
  .plan-name { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 20px; margin-top: 4px; text-transform: capitalize; }
  .plan-lock-badge {
    display: inline-block; font-size: 10px; font-weight: 700;
    background: #f3f4f6; color: #6b7280; padding: 3px 9px; border-radius: 10px; margin-top: 4px;
  }
  .plan-price-big { font-family: 'Nunito', sans-serif; font-size: 28px; font-weight: 900; color: var(--text-dark); }
  .plan-price-sub { font-size: 12px; color: var(--text-light); text-align: right; }
  .plan-zone-adj  { font-size: 11px; text-align: right; margin-top: 2px; }

  .plan-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 14px; }
  .plan-stat { background: var(--gray-bg); border-radius: 12px; padding: 10px 12px; }
  .plan-stat-label { font-size: 11px; color: var(--text-light); }
  .plan-stat-val   { font-family: 'Nunito', sans-serif; font-size: 16px; font-weight: 800; color: var(--text-dark); margin-top: 2px; }

  .plan-ineligible-note {
    margin-top: 12px;
    background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px;
    padding: 8px 12px; font-size: 12px; color: #92400e;
  }

  /* ── Plan CTA button ── */
  .plan-btn {
    width: 100%; padding: 14px; border-radius: 14px;
    font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 15px;
    border: none; cursor: pointer; transition: background 0.2s, opacity 0.2s;
  }
  .plan-btn.primary { background: var(--green-primary); color: white; }
  .plan-btn.primary:hover { background: var(--green-dark); }
  .plan-btn.secondary { background: var(--gray-bg); color: var(--text-light); cursor: not-allowed; }
  .plan-btn.outline { background: transparent; border: 1.5px solid var(--border); color: var(--text-mid); cursor: not-allowed; }

  /* ── Active policy banner ── */
  .active-pol-banner {
    border-radius: 18px;
    padding: 16px 18px;
    border: 1.5px solid;
    margin-bottom: 16px;
  }
  .active-pol-banner.st-active        { background: #f0fdf4; border-color: #bbf7d0; }
  .active-pol-banner.st-grace_period  { background: #fffbeb; border-color: #fde68a; }
  .active-pol-banner.st-lapsed        { background: #fef2f2; border-color: #fecaca; }
  .active-pol-banner.st-cancelled     { background: #f9fafb; border-color: #e5e7eb; }

  .apb-row { display: flex; justify-content: space-between; align-items: flex-start; }
  .apb-tier { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 18px; text-transform: uppercase; }
  .apb-badge { font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 12px; }
  .apb-badge.st-active        { background: #dcfce7; color: #166534; }
  .apb-badge.st-grace_period  { background: #fef9c3; color: #854d0e; }
  .apb-badge.st-lapsed        { background: #fee2e2; color: #991b1b; }
  .apb-badge.st-cancelled     { background: #f3f4f6; color: #374151; }
  .apb-sub { font-size: 12px; color: var(--text-mid); margin-top: 3px; }
  .apb-next-premium { font-size: 12px; color: var(--text-light); margin-top: 2px; }

  .renewal-risk-badge {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 12px;
    margin-top: 6px;
  }
  .renewal-risk-badge.low { background: #dcfce7; color: #166534; }
  .renewal-risk-badge.medium { background: #fef9c3; color: #854d0e; }
  .renewal-risk-badge.high { background: #fee2e2; color: #991b1b; }

  .apb-toggle-row { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
  .rc-toggle {
    position: relative; display: inline-block; width: 44px; height: 24px;
  }
  .rc-toggle input { opacity: 0; width: 0; height: 0; }
  .rc-toggle-slider {
    position: absolute; cursor: pointer; inset: 0; border-radius: 24px;
    background: #d1d5db; transition: background 0.25s;
  }
  .rc-toggle-slider:before {
    content: ''; position: absolute; height: 18px; width: 18px;
    left: 3px; bottom: 3px; background: white; border-radius: 50%;
    transition: transform 0.25s;
  }
  .rc-toggle input:checked + .rc-toggle-slider { background: var(--green-primary); }
  .rc-toggle input:checked + .rc-toggle-slider:before { transform: translateX(20px); }
  .apb-toggle-label { font-size: 13px; color: var(--text-mid); }

  .apb-actions { display: flex; gap: 8px; margin-top: 12px; }
  .apb-action-btn {
    flex: 1; padding: 9px; border-radius: 12px; font-size: 12px; font-weight: 700;
    font-family: 'DM Sans', sans-serif; cursor: pointer; transition: opacity 0.2s;
    border: 1.5px solid var(--border); background: var(--white); color: var(--text-dark);
  }
  .apb-action-btn.danger { color: var(--error); border-color: #fecaca; }
  .apb-action-btn.primary { background: var(--green-primary); color: white; border-color: var(--green-primary); }

  /* ── Eligibility gate ── */
  .eligib-gate {
    border-radius: 14px; padding: 14px 16px;
    border: 1.5px solid #fde68a; background: #fffbeb;
    margin-bottom: 16px;
  }
  .eligib-gate.pass { border-color: #bbf7d0; background: #f0fdf4; }
  .eligib-gate-title { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 14px; }
  .eligib-gate.fail  .eligib-gate-title { color: #92400e; }
  .eligib-gate.pass  .eligib-gate-title { color: #166534; }
  .eligib-gate-sub { font-size: 12px; margin-top: 4px; }
  .eligib-gate.fail .eligib-gate-sub { color: #b45309; }
  .eligib-gate.pass .eligib-gate-sub { color: #15803d; }

  /* ── Exclusions modal ── */
  .excl-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.55);
    display: flex; align-items: flex-end; justify-content: center; z-index: 100;
  }
  .excl-sheet {
    background: var(--white); width: 100%; max-width: 480px;
    border-radius: 24px 24px 0 0; max-height: 90vh;
    display: flex; flex-direction: column;
  }
  .excl-header { padding: 20px 20px 14px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
  .excl-title  { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 20px; color: var(--text-dark); }
  .excl-sub    { font-size: 13px; color: var(--text-mid); margin-top: 3px; }
  .excl-list   { overflow-y: auto; flex: 1; padding: 16px 20px; display: flex; flex-direction: column; gap: 10px; }
  .excl-item   { display: flex; gap: 12px; padding: 12px 14px; background: var(--gray-bg); border: 1px solid var(--border); border-radius: 14px; }
  .excl-item-title { font-size: 13px; font-weight: 700; color: var(--text-dark); }
  .excl-item-desc  { font-size: 11.5px; color: var(--text-mid); margin-top: 2px; }
  .excl-footer { padding: 14px 20px 24px; border-top: 1px solid var(--border); flex-shrink: 0; }
  .excl-check-row { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 14px; cursor: pointer; }
  .excl-check { width: 18px; height: 18px; flex-shrink: 0; accent-color: var(--green-primary); margin-top: 2px; }
  .excl-check-label { font-size: 13px; color: var(--text-dark); }
  .excl-cta {
    width: 100%; padding: 15px; background: var(--green-primary); color: white;
    border: none; border-radius: 14px; font-family: 'Nunito', sans-serif; font-weight: 900;
    font-size: 15px; cursor: pointer; transition: background 0.2s;
  }
  .excl-cta:disabled { background: var(--border); color: var(--text-light); cursor: not-allowed; }
  .excl-cta:not(:disabled):hover { background: var(--green-dark); }
  .excl-view-link {
    width: 100%; text-align: center; font-size: 13px; color: var(--text-mid);
    background: none; border: none; cursor: pointer; padding: 8px;
    font-family: 'DM Sans', sans-serif; text-decoration: underline; margin-top: 16px;
  }

  /* ── Premium breakdown (renewal modal) ── */
  .breakdown-modal-row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 13px; }
  .breakdown-modal-key { color: var(--text-mid); }
  .breakdown-modal-val { font-weight: 600; color: var(--text-dark); }
  .breakdown-modal-val.neg { color: var(--green-dark); }
  .breakdown-modal-total {
    border-top: 1.5px solid var(--border); margin-top: 6px; padding-top: 10px;
    display: flex; justify-content: space-between;
    font-family: 'Nunito', sans-serif; font-weight: 900;
    font-size: 15px; color: var(--text-dark);
  }
  .breakdown-modal-total .val { color: var(--green-dark); text-align: right; }

  /* ── Renewal modal ── */
  .renew-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.55);
    display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px;
  }
  .renew-modal {
    background: var(--white); border-radius: 24px; max-width: 400px; width: 100%;
    padding: 24px; max-height: 90vh; overflow-y: auto;
  }
  .renew-title { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 20px; color: var(--text-dark); margin-bottom: 16px; }
  .tier-chips { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; margin-bottom: 16px; }
  .tier-chip {
    padding: 10px 8px; border-radius: 12px; border: 1.5px solid var(--border);
    text-align: center; cursor: pointer; transition: all 0.2s; background: var(--white);
  }
  .tier-chip.selected { border-color: var(--green-primary); background: var(--green-light); }
  .tier-chip.disabled { opacity: 0.4; cursor: not-allowed; }
  .tier-chip-name  { font-size: 13px; font-weight: 700; text-transform: capitalize; margin-top: 2px; }
  .tier-chip-price { font-size: 11px; color: var(--text-light); }
  .renew-actions { display: flex; gap: 10px; margin-top: 16px; }
  .renew-cancel {
    flex: 1; padding: 13px; border-radius: 14px; border: 1.5px solid var(--border);
    background: transparent; color: var(--text-mid); font-family: 'Nunito', sans-serif;
    font-weight: 700; font-size: 14px; cursor: pointer;
  }
  .renew-confirm {
    flex: 2; padding: 13px; border-radius: 14px; border: none;
    background: var(--green-primary); color: white; font-family: 'Nunito', sans-serif;
    font-weight: 800; font-size: 14px; cursor: pointer;
  }
  .renew-confirm:disabled { background: var(--border); cursor: not-allowed; }

  /* ── Info box ── */
  .info-box { background: var(--gray-bg); border-radius: 16px; padding: 16px 18px; margin-top: 16px; }
  .info-box-title { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 14px; margin-bottom: 10px; }
  .info-box li { font-size: 12.5px; color: var(--text-mid); margin-bottom: 6px; list-style: disc; margin-left: 16px; }
`;

/* ─── Data ──────────────────────────────────────────────────────────────── */
const EXCLUSIONS = [
  { icon: '⚔️', title: 'War and armed conflict', desc: 'Losses arising from war, invasion, or armed hostilities.' },
  { icon: '🦠', title: 'Pandemic / epidemic declaration', desc: 'Disruptions due to a government-declared pandemic or epidemic.' },
  { icon: '☢️', title: 'Nuclear and radioactive events', desc: 'Any loss caused by nuclear, radioactive, or radiation hazard.' },
  { icon: '🏛️', title: 'Government policy or regulatory changes', desc: 'Policy changes, bans, or regulatory decisions by any authority.' },
  { icon: '⚙️', title: 'Platform operational decisions', desc: 'Planned maintenance, algorithm changes, or app updates by Zepto.' },
  { icon: '🙋', title: 'Self-inflicted / voluntary offline', desc: 'Choosing to go offline or voluntarily skipping shifts.' },
  { icon: '🏥', title: 'Health, accident, life', desc: 'Personal health events, accidents, or life insurance claims.' },
  { icon: '🔧', title: 'Vehicle damage and repair', desc: 'Downtime due to vehicle breakdown, servicing, or repair.' },
  { icon: '⏱️', title: 'Disruptions under 45 minutes', desc: 'Any disruption lasting less than 45 minutes is not covered.' },
  { icon: '🗓️', title: 'Claims after 48-hour window', desc: 'Claims must be submitted within 48 hours of the disruption.' },
];

const TIER_META = {
  flex: { icon: '⚡', label: 'Flex', subtitle: 'Part-time · 4–5 hrs/day' },
  standard: { icon: '🛵', label: 'Standard', subtitle: 'Full-time · 8–10 hrs/day' },
  pro: { icon: '🏆', label: 'Pro', subtitle: 'Peak warrior · 12+ hrs/day' }
};

const TIER_LIMITS = {
  flex: { max_payout_day: 250, max_days_week: 2, weekly_premium: 22 },
  standard: { max_payout_day: 400, max_days_week: 3, weekly_premium: 33 },
  pro: { max_payout_day: 500, max_days_week: 4, weekly_premium: 45 },
};

/* ─── ExclusionsScreen ────────────────────────────────────────────────── */
function ExclusionsScreen({ onAccept }) {
  const [checked, setChecked] = useState(false);
  return (
    <div className="excl-overlay">
      <div className="excl-sheet">
        <div className="excl-header">
          <p className="excl-title">⚠️ What's Not Covered</p>
          <p className="excl-sub">Read all 10 exclusions before your first premium is collected.</p>
        </div>
        <div className="excl-list">
          {EXCLUSIONS.map((ex, i) => (
            <div className="excl-item" key={i}>
              <span style={{ fontSize: 22, flexShrink: 0, marginTop: 2 }}>{ex.icon}</span>
              <div>
                <p className="excl-item-title">{ex.title}</p>
                <p className="excl-item-desc">{ex.desc}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="excl-footer">
          <label className="excl-check-row">
            <input className="excl-check" type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} />
            <span className="excl-check-label">I have read and understood all 10 exclusions listed above.</span>
          </label>
          <button className="excl-cta" disabled={!checked} onClick={onAccept}>
            I Understand — Continue to Plans
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── PremiumBreakdown ────────────────────────────────────────────────── */
function PremiumBreakdown({ breakdown }) {
  if (!breakdown) return null;

  return (
    <div style={{ background: '#eff6ff', borderRadius: 14, padding: 14, border: '1px solid #bfdbfe', marginTop: 12 }}>
      <p style={{ fontFamily: 'Nunito, sans-serif', fontWeight: 800, fontSize: 12, color: '#1e40af', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
        Premium Breakdown (Next Week)
      </p>
      
      <div className="breakdown-modal-row">
        <span className="breakdown-modal-key">Base Premium</span>
        <span className="breakdown-modal-val">₹{breakdown.base_premium}</span>
      </div>
      
      {breakdown.activity_multiplier !== 1.0 && (
        <div className="breakdown-modal-row">
          <span className="breakdown-modal-key">Activity Tier</span>
          <span className="breakdown-modal-val text-blue-600">×{breakdown.activity_multiplier}</span>
        </div>
      )}
      {breakdown.zone_risk_adjustment !== 0 && (
        <div className="breakdown-modal-row">
          <span className="breakdown-modal-key">Zone Factor</span>
          <span className="breakdown-modal-val text-red-600">+{breakdown.zone_risk_adjustment}</span>
        </div>
      )}
      {breakdown.loyalty_discount !== 0 && (
        <div className="breakdown-modal-row">
          <span className="breakdown-modal-key">Loyalty Discount</span>
          <span className="breakdown-modal-val text-green-600">-{breakdown.loyalty_discount}</span>
        </div>
      )}

      <div className="breakdown-modal-total">
        <span>Total</span>
        <span className="val">₹{breakdown.total}/week</span>
      </div>
    </div>
  );
}

/* ─── Main Policy ─────────────────────────────────────────────────────── */
export default function Policy() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [activePolicy, setActivePolicy] = useState(null);
  const [eligibility, setEligibility] = useState(null);
  const [breakdown, setBreakdown] = useState(null);
  const [_quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);
  const [cancelling, setCancelling] = useState(false);
  const [showRenewalModal, setShowRenewalModal] = useState(false);
  const [renewalQuote, setRenewalQuote] = useState(null);
  const [selectedRenewalTier, setSelectedRenewalTier] = useState(null);
  const [renewalLoading, setRenewalLoading] = useState(false);
  const [downloadingCert, setDownloadingCert] = useState(false);
  const [togglingAutoRenew, setTogglingAutoRenew] = useState(false);
  const [showExclusions, setShowExclusions] = useState(false);
  const [exclusionsAccepted, setExclusionsAccepted] = useState(false);
  const [pendingTier, setPendingTier] = useState(null);
  const [error, setError] = useState(null);
  const [paymentStatus, setPaymentStatus] = useState(null);

  // Handle Stripe redirect (payment success/cancel)
  useEffect(() => {
    const payment = searchParams.get('payment');
    const sessionId = searchParams.get('session_id');

    if (payment === 'success' && sessionId) {
      setPaymentStatus('confirming');
      api.confirmPayment(sessionId)
        .then(() => {
          setPaymentStatus('success');
          // Clear URL params
          setSearchParams({});
          // Reload policy data
          load();
        })
        .catch((err) => {
          setPaymentStatus('error');
          setError(err.message);
        });
    } else if (payment === 'cancelled') {
      setPaymentStatus('cancelled');
      setSearchParams({});
    }
  }, [searchParams, setSearchParams]);

  useEffect(() => { load(); }, []);

  async function load() {
    try {
      const [pd, elig, breakd, qd] = await Promise.all([
        api.getActivePolicy().catch(() => null),
        api.getPartnerEligibility().catch(() => null),
        api.getPremiumBreakdown().catch(() => null),
        api.getPolicyQuotes().catch(() => [])
      ]);
      setActivePolicy(pd);
      setEligibility(elig);
      setBreakdown(breakd);
      setQuotes(Array.isArray(qd) ? qd : []);
    } catch (e) {
      console.error(e);
      setError(e.message);
    } finally { 
      setLoading(false); 
    }
  }

  function initiatePurchase(tier) {
    if (!exclusionsAccepted) { setPendingTier(tier); setShowExclusions(true); }
    else handlePurchase(tier);
  }

  function onExclusionsAccept() {
    setExclusionsAccepted(true); setShowExclusions(false);
    if (pendingTier) { handlePurchase(pendingTier); setPendingTier(null); }
  }

  async function handlePurchase(tier) {
    setPurchasing(tier);
    try {
      // Create Stripe checkout session and redirect
      const { checkout_url } = await api.createCheckoutSession(tier, false);
      window.location.href = checkout_url;
    }
    catch (e) {
      alert(e.message);
      setPurchasing(null);
    }
    // Don't reset purchasing state - page will redirect to Stripe
  }

  async function handleCancel() {
    if (!window.confirm('Are you sure you want to cancel your policy?')) return;
    setCancelling(true);
    try { await api.cancelPolicy(activePolicy.id); await load(); }
    catch (e) { alert(e.message); }
    finally { setCancelling(false); }
  }

  async function openRenewalModal() {
    setShowRenewalModal(true);
    setSelectedRenewalTier(activePolicy?.tier);
    setRenewalLoading(true);
    try {
      const q = await api.getRenewalQuote(activePolicy.id, activePolicy.tier);
      setRenewalQuote(q);
    } catch (e) { alert(e.message); setShowRenewalModal(false); }
    finally { setRenewalLoading(false); }
  }

  async function handleTierChange(tier) {
    setSelectedRenewalTier(tier); 
    setRenewalLoading(true);
    try {
      const q = await api.getRenewalQuote(activePolicy.id, tier);
      setRenewalQuote(q);
    } catch (e) { console.error(e); }
    finally { setRenewalLoading(false); }
  }

  async function handleRenew() {
    setRenewalLoading(true);
    try {
      await api.renewPolicy(activePolicy.id, selectedRenewalTier !== activePolicy.tier ? selectedRenewalTier : null, activePolicy.auto_renew);
      setShowRenewalModal(false); setRenewalQuote(null); await load();
    } catch (e) { alert(e.message); }
    finally { setRenewalLoading(false); }
  }

  async function handleToggleAutoRenew() {
    setTogglingAutoRenew(true);
    try { 
      // Toggle auto_renew via patch
      await api.updateAutoRenew(activePolicy.id, !activePolicy.auto_renew);
      await load(); 
    }
    catch (e) { alert(e.message); }
    finally { setTogglingAutoRenew(false); }
  }

  async function handleDownloadCert() {
    setDownloadingCert(true);
    try {
      const blob = await api.downloadCertificate(activePolicy.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `policy_certificate_${activePolicy.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch(e) { alert(e.message); }
    finally { setDownloadingCert(false); }
  }

  function countdown() {
    if (!activePolicy) return null;
    if (activePolicy.status === 'active' && activePolicy.days_until_expiry != null) {
      const d = activePolicy.days_until_expiry;
      if (d === 0) return 'Expires today';
      if (d === 1) return 'Expires tomorrow';
      return `Expires in ${d} days`;
    }
    if (activePolicy.status === 'grace_period' && activePolicy.hours_until_grace_ends != null) {
      const h = Math.floor(activePolicy.hours_until_grace_ends);
      return h < 1 ? 'Grace period ending soon' : `Grace period: ${h}h left`;
    }
    return null;
  }

  function getRenewalRisk() {
    if (!activePolicy) return null;
    const daysLeft = activePolicy.days_until_expiry ?? 0;
    const hasAutoRenew = activePolicy.auto_renew;
    const status = activePolicy.status;

    // High risk: expired/cancelled or <7 days with no auto-renew
    if (status === 'lapsed' || status === 'cancelled' || (daysLeft < 7 && !hasAutoRenew)) {
      return { level: 'high', label: 'High renewal risk', icon: '🔴' };
    }
    // Medium risk: 7-14 days or no auto-renew
    if (daysLeft >= 7 && daysLeft <= 14 || !hasAutoRenew) {
      return { level: 'medium', label: 'Monitor renewal', icon: '🟡' };
    }
    // Low risk: >14 days with auto-renew
    return { level: 'low', label: 'Low renewal risk', icon: '🟢' };
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--gray-bg)' }}>
      <div style={{ width: 32, height: 32, border: '3px solid var(--green-light)', borderTopColor: 'var(--green-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
    </div>
  );

  const polSt = activePolicy?.status || 'active';
  const ST_LABELS = { active: 'Active', grace_period: 'Grace Period', lapsed: 'Lapsed', cancelled: 'Cancelled' };
  const cd = countdown();
  const currentTier = activePolicy?.tier || null;
  const gateBlocked = eligibility?.gate_blocked ?? false;
  const renewalRisk = getRenewalRisk();

  return (
    <>
      <style>{S}</style>
      <div className="pol-wrap" style={{ padding: '24px 16px', background: 'var(--gray-bg)', minHeight: '100vh' }}>

        {/* Exclusions modal */}
        {showExclusions && <ExclusionsScreen onAccept={onExclusionsAccept} />}

        {/* Header */}
        <div style={{ marginBottom: 16 }}>
          <h1 className="pol-page-title">Insurance Plans</h1>
          <p className="pol-page-sub">Choose coverage that fits your activity level</p>
        </div>

        {error && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '12px', borderRadius: '12px', color: '#991b1b', fontSize: 13, marginBottom: 16 }}>
            {error}
          </div>
        )}

        {/* Payment status banner */}
        {paymentStatus === 'confirming' && (
          <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', padding: '16px', borderRadius: '12px', color: '#1e40af', fontSize: 14, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 20, height: 20, border: '2px solid #bfdbfe', borderTopColor: '#3b82f6', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            Confirming your payment...
          </div>
        )}
        {paymentStatus === 'success' && (
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '16px', borderRadius: '12px', color: '#166534', fontSize: 14, marginBottom: 16 }}>
            ✅ Payment successful! Your policy is now active.
          </div>
        )}
        {paymentStatus === 'cancelled' && (
          <div style={{ background: '#fffbeb', border: '1px solid #fde68a', padding: '16px', borderRadius: '12px', color: '#92400e', fontSize: 14, marginBottom: 16 }}>
            Payment was cancelled. You can try again below.
          </div>
        )}

        {/* Demo mode notice */}
        <div style={{ background: '#faf5ff', border: '1px solid #e9d5ff', padding: '10px 14px', borderRadius: '10px', color: '#6b21a8', fontSize: 12, marginBottom: 16 }}>
          🧪 <strong>Demo Mode:</strong> Stripe test mode - no real money charged. Use card <code style={{ background: '#ede9fe', padding: '2px 6px', borderRadius: 4 }}>4242 4242 4242 4242</code>
        </div>

        {/* Eligibility gate */}
        {gateBlocked && (
          <div className="eligib-gate fail">
            <p className="eligib-gate-title">
              ⏳ Cover starts after 7 active delivery days
            </p>
            <p className="eligib-gate-sub">
              You have <strong>{eligibility?.active_days_last_30 ?? 0}</strong> active days.
              Complete 7 days to unlock coverage.
            </p>
          </div>
        )}

        {/* Active policy banner */}
        {activePolicy && (
          <div className={`active-pol-banner st-${polSt}`}>
            <div className="apb-row">
              <div>
                <p className="apb-tier">{activePolicy.tier.toUpperCase()} Plan</p>
                <p className="apb-sub">{cd || `Expires ${new Date(activePolicy.expires_at).toLocaleDateString('en-IN')}`}</p>
                <p className="apb-next-premium">Next week: ₹{breakdown?.next_week_premium ?? breakdown?.total ?? TIER_LIMITS[activePolicy.tier].weekly_premium}/week</p>
                {renewalRisk && (
                  <span className={`renewal-risk-badge ${renewalRisk.level}`}>
                    {renewalRisk.icon} {renewalRisk.label}
                  </span>
                )}
              </div>
              <span className={`apb-badge st-${polSt}`}>{ST_LABELS[polSt]}</span>
            </div>
            {activePolicy.can_renew && (
              <div className="apb-toggle-row">
                <label className="rc-toggle">
                  <input type="checkbox" checked={!!activePolicy.auto_renew} onChange={handleToggleAutoRenew} disabled={togglingAutoRenew} />
                  <span className="rc-toggle-slider" />
                </label>
                <span className="apb-toggle-label">Auto-renewal</span>
              </div>
            )}
            <div className="apb-actions">
              {activePolicy.can_renew && (
                <button className="apb-action-btn primary" onClick={openRenewalModal}>Renew</button>
              )}
              <button className="apb-action-btn" onClick={handleDownloadCert} disabled={downloadingCert}>
                {downloadingCert ? 'Downloading…' : 'Certificate'}
              </button>
              {(polSt === 'active' || polSt === 'grace_period') && (
                <button className="apb-action-btn danger" onClick={handleCancel} disabled={cancelling}>
                  {cancelling ? 'Wait...' : 'Cancel'}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Plan cards */}
        {['flex', 'standard', 'pro'].map(tier => {
          const isCurrent = currentTier === tier;
          const isBlocked = eligibility?.blocked_tiers?.includes(tier) ?? gateBlocked;
          const meta = TIER_META[tier];
          const limits = TIER_LIMITS[tier];
          const displayPremium = isCurrent && breakdown?.total ? breakdown.total : limits.weekly_premium;
          const reason = eligibility?.reasons?.[tier];

          return (
            <div key={tier} className={`pol-card ${isCurrent ? 'ring-active' : ''} ${isBlocked ? 'locked' : ''}`} style={{ marginBottom: 12 }}>
              <div className="pol-card-body">
                <div className="plan-hdr">
                  <div>
                    <span className="plan-icon">{meta.icon}</span>
                    <p className="plan-name">{meta.label}</p>
                    {isBlocked && <span className="plan-lock-badge">🔒 Locked</span>}
                    {isCurrent && <span className="plan-lock-badge" style={{background: 'var(--green-primary)', color:'white'}}>✅ Current</span>}
                  </div>
                  <div>
                    <p className="plan-price-big">₹{displayPremium}</p>
                    <p className="plan-price-sub">/week</p>
                  </div>
                </div>

                {isBlocked && reason && !gateBlocked && (
                  <div className="plan-ineligible-note">ℹ️ {reason}</div>
                )}

                <div className="plan-stats">
                  <div className="plan-stat">
                    <p className="plan-stat-label">Daily Payout</p>
                    <p className="plan-stat-val">₹{limits.max_payout_day}</p>
                  </div>
                  <div className="plan-stat">
                    <p className="plan-stat-label">Max Days/Week</p>
                    <p className="plan-stat-val">{limits.max_days_week}</p>
                  </div>
                </div>
              </div>
              <div className="pol-card-footer">
                <button
                  className={`plan-btn ${isCurrent || isBlocked || activePolicy ? 'secondary' : 'primary'}`}
                  disabled={!!activePolicy || isBlocked || purchasing === tier}
                  onClick={() => initiatePurchase(tier)}
                >
                  {purchasing === tier ? 'Processing…' : 
                   isCurrent ? 'Current Plan' : 
                   activePolicy ? 'Already Covered' : 
                   isBlocked ? 'Not Eligible' : 'Get This Plan'}
                </button>
              </div>
            </div>
          );
        })}

        <button className="excl-view-link" onClick={() => setShowExclusions(true)}>
          ⚠️ View all 10 policy exclusions
        </button>

        <div className="info-box">
          <p className="info-box-title">How it works:</p>
          <ul>
            <li>Pay weekly premium via UPI</li>
            <li>Automatic payout when trigger events occur</li>
            <li>No claim forms — events detected automatically</li>
            <li>Money credited to your UPI within minutes</li>
            <li>48-hour grace period after expiry for renewal</li>
          </ul>
        </div>

        {/* Payout Proof Ledger */}
        {(activePolicy || user?.zone_id) && (
          <PayoutLedger zoneId={activePolicy?.zone_id || user?.zone_id} />
        )}

        {/* Renewal modal */}
        {showRenewalModal && (
          <div className="renew-overlay">
            <div className="renew-modal">
              <p className="renew-title">Renew Your Policy</p>
              <p style={{ fontSize: 12, color: 'var(--text-light)', marginBottom: 12 }}>Select Plan</p>
              
              <div className="tier-chips">
                {['flex', 'standard', 'pro'].map(tier => {
                  const el = eligibility?.allowed_tiers?.includes(tier) ?? true;
                  return (
                    <div
                      key={tier}
                      className={`tier-chip ${selectedRenewalTier === tier ? 'selected' : ''} ${!el ? 'disabled' : ''}`}
                      onClick={() => el && handleTierChange(tier)}
                    >
                      <div style={{ fontSize: 20 }}>{TIER_META[tier].icon}</div>
                      <p className="tier-chip-name">{tier}</p>
                      <p className="tier-chip-price">₹{TIER_LIMITS[tier].weekly_premium}</p>
                    </div>
                  );
                })}
              </div>

              {renewalLoading ? (
                <div style={{ textAlign: 'center', padding: 24 }}>
                  <div style={{ width: 28, height: 28, border: '3px solid var(--green-light)', borderTopColor: 'var(--green-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto' }} />
                </div>
              ) : renewalQuote ? (
                <PremiumBreakdown breakdown={{
                  base_premium: renewalQuote.base_premium,
                  activity_multiplier: renewalQuote.activity_multiplier || 1,
                  zone_risk_adjustment: renewalQuote.zone_risk_adjustment || 0,
                  loyalty_discount: renewalQuote.loyalty_discount_applied || 0,
                  total: renewalQuote.final_premium
                }} />
              ) : null}

              <div className="renew-actions">
                <button className="renew-cancel" onClick={() => { setShowRenewalModal(false); setRenewalQuote(null); }}>Cancel</button>
                <button className="renew-confirm" onClick={handleRenew} disabled={renewalLoading || !renewalQuote}>
                  {renewalLoading ? 'Processing…' : 'Confirm Renewal'}
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </>
  );
}