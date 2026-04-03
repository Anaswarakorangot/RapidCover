/**
 * Dashboard.jsx  –  RapidCover Partner Home
 *
 * Person 1 Phase 2:
 *   - Removed ALL hardcoded constants: zoneReassignment, weatherAlert, streakWeeks
 *   - All state comes from GET /partners/me/experience-state
 *   - Polls every 5 s during active drills; stops after 2 min of inactivity
 *   - Shows strong payout banner when latest_payout.status === "paid"
 *   - Zone alert / reassignment cards only render when backend sends them (non-null)
 *
 * UI: Original green theme preserved (matching Register.jsx / Login.jsx design system).
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { getMyReassignments, acceptReassignment, rejectReassignment } from '../services/proofApi';
import { useAuth } from '../context/AuthContext';
import SourceBadge from '../components/SourceBadge';
import ReassignmentCountdown from '../components/ReassignmentCountdown';

const POLL_INTERVAL_MS = 5_000;
const POLL_TIMEOUT_MS  = 120_000;

/* ─── Design Tokens (identical to Login.jsx & Register.jsx) ──────────────── */
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

  .dash-wrap {
    font-family: 'DM Sans', sans-serif;
    color: var(--text-dark);
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-bottom: 24px;
  }

  /* ── Card ── */
  .rc-card {
    background: var(--white);
    border-radius: 20px;
    border: 1.5px solid var(--border);
    overflow: hidden;
  }
  .rc-card-body { padding: 16px 18px; }

  /* ── Section titles ── */
  .rc-section-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    font-size: 15px;
    color: var(--text-dark);
    margin-bottom: 12px;
  }

  /* ── Coverage hero card ── */
  .policy-hero {
    border-radius: 20px;
    padding: 20px 18px;
    color: white;
    position: relative;
    overflow: hidden;
  }
  .policy-hero.flex-tier     { background: linear-gradient(135deg, #059669, #10b981); }
  .policy-hero.standard-tier { background: linear-gradient(135deg, #2563eb, #3b82f6); }
  .policy-hero.pro-tier      { background: linear-gradient(135deg, #7c3aed, #8b5cf6); }
  .policy-hero.no-policy     { background: linear-gradient(135deg, #6b7280, #9ca3af); }

  .policy-hero-label  { font-size: 11px; opacity: 0.75; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
  .policy-hero-tier   { font-family: 'Nunito', sans-serif; font-size: 26px; font-weight: 900; margin-top: 2px; text-transform: capitalize; }
  .policy-hero-badge  {
    position: absolute; top: 16px; right: 16px;
    background: rgba(255,255,255,0.25); border-radius: 20px;
    font-size: 11px; font-weight: 700; padding: 4px 10px;
  }
  .policy-hero-grid   { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; margin-top: 16px; }
  .policy-hero-stat-label { font-size: 10px; opacity: 0.7; }
  .policy-hero-stat-val   { font-family: 'Nunito', sans-serif; font-size: 18px; font-weight: 800; }
  .policy-hero-footer { margin-top: 14px; display: flex; align-items: center; justify-content: space-between; }
  .policy-hero-expires { font-size: 11px; opacity: 0.7; }
  .policy-hero-btn {
    font-size: 11px; background: rgba(255,255,255,0.2); color: white;
    border: none; border-radius: 20px; padding: 6px 14px; cursor: pointer;
    font-family: 'DM Sans', sans-serif; font-weight: 600;
  }
  .policy-hero-btn:hover { background: rgba(255,255,255,0.3); }

  /* ── Alert cards ── */
  .alert-card {
    border-radius: 16px;
    padding: 14px 16px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }
  .alert-orange { background: #fff7ed; border: 1.5px solid #fed7aa; }
  .alert-blue   { background: #eff6ff; border: 1.5px solid #bfdbfe; }
  .alert-red    { background: #fef2f2; border: 1.5px solid #fecaca; }
  .alert-green  { background: #f0fdf4; border: 1.5px solid #bbf7d0; }
  .alert-purple { background: #faf5ff; border: 1.5px solid #e9d5ff; }
  .alert-title  { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 13px; }
  .alert-orange .alert-title { color: #9a3412; }
  .alert-blue   .alert-title { color: #1e40af; }
  .alert-red    .alert-title { color: #991b1b; }
  .alert-green  .alert-title { color: #166534; }
  .alert-purple .alert-title { color: #6b21a8; }
  .alert-body   { font-size: 12px; margin-top: 2px; line-height: 1.5; }
  .alert-orange .alert-body { color: #c2410c; }
  .alert-blue   .alert-body { color: #1d4ed8; }
  .alert-red    .alert-body { color: #dc2626; }
  .alert-green  .alert-body { color: #166534; }
  .alert-purple .alert-body { color: #6b21a8; }

  .alert-actions { display: flex; gap: 8px; margin-top: 10px; }
  .alert-btn-outline {
    flex: 1; padding: 7px; border-radius: 10px; font-size: 12px; font-weight: 600;
    border: 1.5px solid #f97316; color: #9a3412; background: transparent; cursor: pointer;
    font-family: 'DM Sans', sans-serif;
  }
  .alert-btn-fill {
    flex: 2; padding: 7px; border-radius: 10px; font-size: 12px; font-weight: 600;
    border: none; color: white; background: #f97316; cursor: pointer;
    font-family: 'DM Sans', sans-serif;
  }
  .alert-badge {
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 12px;
    margin-left: auto;
  }
  .alert-orange .alert-badge { background: #ffedd5; color: #9a3412; }
  .alert-blue   .alert-badge { background: #dbeafe; color: #1e40af; }
  .alert-green  .alert-badge { background: #dcfce7; color: #166534; }
  .alert-purple .alert-badge { background: #ede9fe; color: #6b21a8; }

  /* ── Payout banner ── */
  .payout-banner {
    background: linear-gradient(135deg, var(--green-primary), var(--green-dark));
    border-radius: 20px;
    padding: 16px 18px;
    color: white;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    position: relative;
    box-shadow: 0 6px 20px rgba(61,184,92,0.35);
  }
  .payout-banner-title   { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 17px; }
  .payout-banner-sub     { font-size: 13px; opacity: 0.9; margin-top: 2px; }
  .payout-banner-time    { font-size: 11px; opacity: 0.7; margin-top: 4px; }
  .payout-banner-dismiss {
    position: absolute; top: 12px; right: 14px;
    background: rgba(255,255,255,0.2); border: none; color: white;
    font-size: 16px; width: 24px; height: 24px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; line-height: 1;
  }
  .payout-banner-dismiss:hover { background: rgba(255,255,255,0.35); }

  /* ── Streak bar ── */
  .streak-bar-wrap { margin-bottom: 8px; }
  .streak-bar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
  .streak-bar-label  { font-size: 12px; color: var(--text-mid); }
  .streak-bar-val    { font-size: 12px; font-weight: 700; }
  .streak-track { background: #e5e7eb; border-radius: 99px; height: 7px; overflow: hidden; }
  .streak-fill  { height: 7px; border-radius: 99px; transition: width 0.5s ease; }
  .streak-fill.green  { background: #22c55e; }
  .streak-fill.blue   { background: #3b82f6; }
  .streak-fill.purple { background: #8b5cf6; }
  .streak-fill.amber  { background: #f59e0b; }

  /* ── Premium breakdown ── */
  .breakdown-row { display: flex; justify-content: space-between; align-items: baseline; padding: 4px 0; font-size: 13px; }
  .breakdown-key  { color: var(--text-mid); }
  .breakdown-note { font-size: 11px; color: var(--text-light); margin-left: 4px; }
  .breakdown-val  { font-weight: 600; color: var(--text-dark); }
  .breakdown-val.positive { color: #f97316; }
  .breakdown-val.negative { color: #22c55e; }
  .breakdown-total { border-top: 1.5px solid var(--border); margin-top: 6px; padding-top: 8px; display: flex; justify-content: space-between; }
  .breakdown-total-key { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 14px; color: var(--text-dark); }
  .breakdown-total-val { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 16px; color: var(--green-dark); }

  /* ── Trigger chips ── */
  .trigger-chip {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px; border-radius: 12px; border: 1px solid;
    font-size: 13px; margin-bottom: 8px;
  }

  /* ── Quick action tiles ── */
  .qa-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .qa-tile {
    background: var(--white); border: 1.5px solid var(--border); border-radius: 18px;
    padding: 16px 12px; text-align: center; text-decoration: none;
    transition: box-shadow 0.2s, transform 0.2s;
  }
  .qa-tile:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-1px); }
  .qa-tile-icon  { font-size: 24px; }
  .qa-tile-label { font-size: 12px; font-weight: 600; color: var(--text-dark); margin-top: 6px; font-family: 'Nunito', sans-serif; }

  /* ── Earnings tiles ── */
  .earn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .earn-tile  { background: var(--white); border: 1.5px solid var(--border); border-radius: 18px; padding: 16px; text-align: center; }
  .earn-label  { font-size: 11px; color: var(--text-light); margin-bottom: 4px; }
  .earn-amount { font-family: 'Nunito', sans-serif; font-size: 22px; font-weight: 900; }
  .earn-claims { font-size: 11px; color: var(--text-light); margin-top: 2px; }

  /* ── Claims list ── */
  .claim-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 0; border-bottom: 1px solid var(--border);
  }
  .claim-row:last-child { border-bottom: none; }
  .claim-label { font-size: 13px; font-weight: 600; color: var(--text-dark); }
  .claim-date  { font-size: 11px; color: var(--text-light); margin-top: 1px; }
  .claim-amount { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 15px; color: var(--text-dark); text-align: right; }
  .claim-status {
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px;
    text-align: right; margin-top: 2px; display: inline-block;
  }
  .st-paid     { background: #dcfce7; color: #166534; }
  .st-pending  { background: #fef9c3; color: #854d0e; }
  .st-approved { background: #dbeafe; color: #1e40af; }
  .st-rejected { background: #fee2e2; color: #991b1b; }

  /* ── Coverage list ── */
  .cov-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; font-size: 13px; color: var(--text-mid); }

  /* ── Section header with action ── */
  .sec-hdr { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
  .sec-hdr-link { font-size: 12px; font-weight: 600; color: var(--green-dark); text-decoration: none; }

  /* ── Monday badge ── */
  .monday-badge {
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px;
    background: #dbeafe; color: #1e40af; margin-left: 8px;
  }

  /* ── Toggle button ── */
  .rc-toggle-btn {
    font-size: 11px; font-weight: 600; color: var(--green-dark); background: var(--green-light);
    border: none; border-radius: 20px; padding: 4px 12px; cursor: pointer; font-family: 'DM Sans', sans-serif;
  }

  /* ── No policy CTA ── */
  .no-policy-cta { text-align: center; padding: 28px 16px; }
  .no-policy-icon  { font-size: 48px; }
  .no-policy-title { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 18px; color: var(--text-dark); margin: 10px 0 6px; }
  .no-policy-sub   { font-size: 13px; color: var(--text-mid); margin-bottom: 18px; }
  .rc-btn-primary {
    display: inline-block; background: var(--green-primary); color: white;
    border: none; border-radius: 14px; padding: 13px 28px; font-family: 'Nunito', sans-serif;
    font-weight: 800; font-size: 15px; cursor: pointer; text-decoration: none;
    transition: background 0.2s;
  }
  .rc-btn-primary:hover { background: var(--green-dark); }

  /* ── Live badge ── */
  .live-badge {
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px;
    background: var(--green-light); color: var(--green-dark);
    display: inline-flex; align-items: center; gap: 4px;
  }
  .live-dot {
    width: 6px; height: 6px; background: var(--green-primary);
    border-radius: 50%; animation: pulse 1.5s infinite;
  }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
  @keyframes spin   { to { transform: rotate(360deg); } }
`;

/* ─── Helpers ─────────────────────────────────────────────────────────────── */

const TRIGGER_INFO = {
  rain:     { icon: '🌧️', label: 'Heavy Rain',      color: '#eff6ff', border: '#bfdbfe', text: '#1e40af' },
  heat:     { icon: '🌡️', label: 'Extreme Heat',    color: '#fef2f2', border: '#fecaca', text: '#991b1b' },
  aqi:      { icon: '💨', label: 'Dangerous AQI',   color: '#fffbeb', border: '#fde68a', text: '#92400e' },
  shutdown: { icon: '🚫', label: 'Civic Shutdown',   color: '#faf5ff', border: '#e9d5ff', text: '#6b21a8' },
  closure:  { icon: '🏪', label: 'Store Closure',    color: '#f9fafb', border: '#e5e7eb', text: '#374151' },
};
const STATUS_CLS = { paid: 'st-paid', pending: 'st-pending', approved: 'st-approved', rejected: 'st-rejected' };
const BASES      = { flex: 22, standard: 33, pro: 45 };
const COV_EVENTS = [
  { icon: '🌧️', label: 'Heavy Rain & Floods' },
  { icon: '🌡️', label: 'Extreme Heat (>43°C)' },
  { icon: '💨', label: 'Dangerous AQI (>400)' },
  { icon: '🚫', label: 'Curfew & Bandh' },
  { icon: '🏪', label: 'Dark Store Closures' },
];

/* ─── Sub-components ──────────────────────────────────────────────────────── */

/** Shown prominently at top when a paid claim exists */
function PayoutBanner({ payout, onDismiss }) {
  if (!payout || payout.status !== 'paid') return null;
  return (
    <div className="payout-banner">
      <span style={{ fontSize: 28 }}>💸</span>
      <div style={{ flex: 1 }}>
        <p className="payout-banner-title">Money Sent!</p>
        <p className="payout-banner-sub">
          ₹{payout.amount} paid via UPI{payout.upi_ref ? ` · Ref: ${payout.upi_ref}` : ''}
        </p>
        {payout.paid_at && (
          <p className="payout-banner-time">
            {new Date(payout.paid_at).toLocaleString('en-IN', {
              day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
            })}
          </p>
        )}
      </div>
      <button className="payout-banner-dismiss" onClick={onDismiss} aria-label="Dismiss">×</button>
    </div>
  );
}

/** Only renders when backend sends a non-null zone_alert */
function ZoneAlertCard({ alert }) {
  if (!alert) return null;
  const alertClass = alert.severity === 'high' || alert.severity === 'critical' ? 'alert-red' : 'alert-blue';
  const icon = TRIGGER_INFO[alert.type]?.icon || '⚠️';
  return (
    <div className={`alert-card ${alertClass}`}>
      <span style={{ fontSize: 22 }}>{icon}</span>
      <div>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span className="alert-title">48-Hour {alert.type?.charAt(0).toUpperCase() + alert.type?.slice(1)} Alert</span>
          <span className="alert-badge">{alert.severity?.toUpperCase()}</span>
        </div>
        <p className="alert-body">{alert.message}</p>
        <p style={{ fontSize: 11, color: '#3b82f6', marginTop: 4 }}>Keep your documents handy for quick claims.</p>
      </div>
    </div>
  );
}

/** Only renders when pending reassignment exists */
function ZoneReassignmentCard({ card, onAccept, onDismiss, processing }) {
  if (!card) return null;
  const { old_zone, new_zone, premium_delta, expires_at } = card;
  return (
    <div className="alert-card alert-orange">
      <span style={{ fontSize: 22 }}>📍</span>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span className="alert-title">Zone Reassignment</span>
          {expires_at && <ReassignmentCountdown expiresAt={expires_at} onExpire={onDismiss} />}
        </div>
        <p className="alert-body">
          Your zone is changing from <strong>{old_zone}</strong> to <strong>{new_zone}</strong>.
          {premium_delta !== 0 && (
            <span style={{ color: premium_delta > 0 ? '#166534' : '#c2410c' }}>
              {' '}Premium {premium_delta > 0 ? `-₹${premium_delta}` : `+₹${Math.abs(premium_delta)}`}/week.
            </span>
          )}
        </p>
        <div className="alert-actions">
          <button
            className="alert-btn-outline"
            onClick={onDismiss}
            disabled={processing}
          >
            {processing ? 'Processing...' : 'Decline'}
          </button>
          <button
            className="alert-btn-fill"
            onClick={onAccept}
            disabled={processing}
          >
            {processing ? 'Processing...' : 'Accept New Zone'}
          </button>
        </div>
      </div>
    </div>
  );
}

/** Loyalty/streak progress bars – same visual as original */
function StreakProgressBar({ loyalty }) {
  if (!loyalty) return null;
  const { streak_weeks, next_milestone } = loyalty;
  const w4  = Math.min((streak_weeks / 4)  * 100, 100);
  const w12 = Math.min((streak_weeks / 12) * 100, 100);
  const done4  = streak_weeks >= 4;
  const done12 = streak_weeks >= 12;

  return (
    <div className="rc-card">
      <div className="rc-card-body">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <span className="rc-section-title" style={{ marginBottom: 0 }}>🔥 Loyalty Streak</span>
          <span style={{ fontSize: 12, color: 'var(--text-light)', fontWeight: 600 }}>
            {streak_weeks} week{streak_weeks !== 1 ? 's' : ''} active
          </span>
        </div>
        <div className="streak-bar-wrap">
          <div className="streak-bar-header">
            <span className="streak-bar-label">{done4 ? '✅' : '🎯'} 4-week milestone (6% off)</span>
            <span className="streak-bar-val" style={{ color: done4 ? '#22c55e' : 'var(--text-mid)' }}>
              {done4 ? 'Unlocked!' : `${streak_weeks}/4 wks`}
            </span>
          </div>
          <div className="streak-track">
            <div className={`streak-fill ${done4 ? 'green' : 'blue'}`} style={{ width: `${w4}%` }} />
          </div>
        </div>
        <div className="streak-bar-wrap" style={{ marginTop: 12 }}>
          <div className="streak-bar-header">
            <span className="streak-bar-label">{done12 ? '✅' : '🏆'} 12-week milestone (10% off)</span>
            <span className="streak-bar-val" style={{ color: done12 ? '#22c55e' : 'var(--text-mid)' }}>
              {done12 ? 'Unlocked!' : `${streak_weeks}/12 wks`}
            </span>
          </div>
          <div className="streak-track">
            <div className={`streak-fill ${done12 ? 'green' : 'purple'}`} style={{ width: `${w12}%` }} />
          </div>
        </div>
        {!done4 && (
          <p style={{ fontSize: 11, color: 'var(--text-light)', marginTop: 10 }}>
            Keep your policy active every week to unlock loyalty discounts.
          </p>
        )}
      </div>
    </div>
  );
}

/** Premium breakdown – collapsible, same design as original */
export function WeeklyPremiumBreakdown({ breakdown, policy }) {
  const today    = new Date();
  const isMonday = today.getDay() === 1;
  const [open, setOpen] = useState(isMonday);

  // Only render if we have a policy
  if (!policy) return null;

  // Show unavailable state when backend breakdown is not available
  // (B2: removed hardcoded fallback values per phase 2 requirements)
  if (!breakdown) {
    return (
      <div className="rc-card">
        <div className="rc-card-body">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span className="rc-section-title" style={{ marginBottom: 0 }}>📊 Premium Breakdown</span>
              {isMonday && <span className="monday-badge">This week</span>}
            </div>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-light)', marginTop: 8 }}>
            Premium breakdown is unavailable right now. Check back later.
          </p>
        </div>
      </div>
    );
  }

  const rows = [
    { label: 'Base Premium',       note: policy?.tier ? `${policy.tier} plan` : '',      val: `₹${breakdown.base}`,                cls: '' },
    { label: 'Zone Risk Factor',   note: 'Zone surcharge',                                val: `+₹${breakdown.zone_risk}`,          cls: 'positive' },
    { label: 'Seasonal Index',     note: 'City-specific monthly',                         val: `×${Number(breakdown.seasonal_index).toFixed(2)}`,  cls: '' },
    { label: 'RIQI Adjustment',    note: breakdown.riqi_band || '',                        val: `×${Number(breakdown.riqi_adjustment).toFixed(2)}`, cls: 'positive' },
    { label: 'Activity Tier Factor', note: policy?.tier || '',                             val: `×${Number(breakdown.activity_factor).toFixed(2)}`, cls: '' },
    { label: 'Loyalty Discount',   note: breakdown.loyalty_weeks ? `${breakdown.loyalty_weeks}-week streak` : '4-week streak', val: `×${Number(breakdown.loyalty_discount).toFixed(2)}`, cls: 'negative' },
    { label: 'Platform Fee',       note: 'Waived',                                        val: '₹0',                                cls: '' },
  ];
  const total = breakdown.total;

  return (
    <div className="rc-card">
      <div className="rc-card-body">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span className="rc-section-title" style={{ marginBottom: 0 }}>📊 Premium Breakdown</span>
            {isMonday && <span className="monday-badge">This week</span>}
          </div>
          <button className="rc-toggle-btn" onClick={() => setOpen(v => !v)}>{open ? 'Hide' : 'Show'}</button>
        </div>

        {!open ? (
          <p style={{ fontSize: 13, color: 'var(--text-mid)', marginTop: 8 }}>
            Total: <strong style={{ color: 'var(--text-dark)' }}>₹{total}/week</strong>
          </p>
        ) : (
          <div style={{ marginTop: 12 }}>
            {rows.map(r => (
              <div className="breakdown-row" key={r.label}>
                <span className="breakdown-key">
                  {r.label}
                  {r.note && <span className="breakdown-note">({r.note})</span>}
                </span>
                <span className={`breakdown-val ${r.cls}`}>{r.val}</span>
              </div>
            ))}
            <div className="breakdown-total">
              <span className="breakdown-total-key">Total This Week</span>
              <span className="breakdown-total-val">₹{total}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Main Dashboard ─────────────────────────────────────────────────────── */

export function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [expState,      setExpState]      = useState(null);
  const [policy,        setPolicy]        = useState(null);
  const [summary,       setSummary]       = useState(null);
  const [zone,          setZone]          = useState(null);
  const [triggers,      setTriggers]      = useState([]);
  const [recentClaims,  setRecentClaims]  = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState(null);
  const [payoutDismissed,   setPayoutDismissed]   = useState(false);
  const [reassignDismissed, setReassignDismissed] = useState(false);
  const [pollingActive, setPollingActive] = useState(true);
  const [pendingReassignment, setPendingReassignment] = useState(null);
  const [reassignProcessing, setReassignProcessing] = useState(false);

  const pollRef         = useRef(null);
  const activityRef     = useRef(null);
  const seenPayoutIdRef = useRef(null);

  /* ── idle timer ── */
  const resetActivityTimer = useCallback(() => {
    if (activityRef.current) clearTimeout(activityRef.current);
    setPollingActive(true);
    activityRef.current = setTimeout(() => setPollingActive(false), POLL_TIMEOUT_MS);
  }, []);

  /* ── fetch all in parallel ── */
  const fetchAll = useCallback(async (isInitial = false) => {
    try {
      const [expRes, polRes, sumRes, claimsRes, reassignRes] = await Promise.allSettled([
        api.getPartnerExperienceState().catch(() => null),
        api.getActivePolicy().catch(() => null),
        api.getClaimsSummary().catch(() => null),
        api.getClaims({ limit: 5 }).catch(() => ({ claims: [] })),
        getMyReassignments().catch(() => ({ reassignments: [] })),
      ]);

      if (expRes.status === 'fulfilled' && expRes.value) {
        const exp = expRes.value;
        setExpState(exp);
        const lp = exp.latest_payout;
        if (lp?.status === 'paid' && lp.claim_id !== seenPayoutIdRef.current) {
          seenPayoutIdRef.current = lp.claim_id;
          setPayoutDismissed(false);
        }
        if (exp.zone_alert) resetActivityTimer();
      }

      if (polRes.status === 'fulfilled')    setPolicy(polRes.value);
      if (sumRes.status === 'fulfilled')    setSummary(sumRes.value);
      if (claimsRes.status === 'fulfilled') {
        const raw = claimsRes.value;
        // API may return {claims:[]} or a plain array
        setRecentClaims(Array.isArray(raw) ? raw : (raw?.claims || []));
      }

      // Get pending reassignment (status === 'proposed')
      if (reassignRes.status === 'fulfilled' && reassignRes.value) {
        console.log('[Dashboard] Reassignments response:', reassignRes.value);
        const allReassignments = reassignRes.value.reassignments || [];
        const pending = allReassignments.find(r => r.status === 'proposed');
        console.log('[Dashboard] Pending reassignment:', pending);
        if (pending && !reassignDismissed) {
          setPendingReassignment(pending);
        }
      }

      // Also load zone & active triggers if we have a zone_id
      if (isInitial && user?.zone_id) {
        const z  = await api.getZone(user.zone_id).catch(() => null);
        const tr = await api.getActiveTriggers(user.zone_id).catch(() => ({ triggers: [] }));
        setZone(z);
        setTriggers(tr.triggers || []);
      }

      if (isInitial) setError(null);
    } catch (err) {
      if (isInitial) setError(err.message);
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [user?.zone_id, resetActivityTimer, reassignDismissed]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchAll(true);
    resetActivityTimer();
    return () => {
      if (pollRef.current)    clearInterval(pollRef.current);
      if (activityRef.current) clearTimeout(activityRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (pollingActive) {
      pollRef.current = setInterval(() => fetchAll(false), POLL_INTERVAL_MS);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [pollingActive, fetchAll]);

  /* ── reassignment accept/reject handlers ── */
  const handleAcceptReassignment = async () => {
    if (!pendingReassignment?.id) return;
    setReassignProcessing(true);
    try {
      await acceptReassignment(pendingReassignment.id);
      setPendingReassignment(null);
      setReassignDismissed(true);
      // Refresh to get updated zone_id
      fetchAll(false);
    } catch (err) {
      console.error('Failed to accept reassignment:', err);
    } finally {
      setReassignProcessing(false);
    }
  };

  const handleRejectReassignment = async () => {
    if (!pendingReassignment?.id) return;
    setReassignProcessing(true);
    try {
      await rejectReassignment(pendingReassignment.id);
      setPendingReassignment(null);
      setReassignDismissed(true);
    } catch (err) {
      console.error('Failed to reject reassignment:', err);
    } finally {
      setReassignProcessing(false);
    }
  };

  /* ── derived ── */
  const zoneAlert       = expState?.zone_alert       ?? null;
  const loyalty         = expState?.loyalty          ?? null;
  const premiumBreakdown = expState?.premium_breakdown ?? null;
  const latestPayout    = expState?.latest_payout    ?? null;

  // Build reassignment card data from pending reassignment (has ID for API calls)
  const zoneReassignmentCard = pendingReassignment ? {
    old_zone: pendingReassignment.old_zone_name || `Zone #${pendingReassignment.old_zone_id}`,
    new_zone: pendingReassignment.new_zone_name || `Zone #${pendingReassignment.new_zone_id}`,
    premium_delta: pendingReassignment.premium_adjustment || 0,
    expires_at: pendingReassignment.expires_at,
  } : null;

  const daysLeft  = policy ? Math.ceil((new Date(policy.expires_at) - new Date()) / 864e5) : 0;
  const tierClass = { flex: 'flex-tier', standard: 'standard-tier', pro: 'pro-tier' }[policy?.tier] || 'no-policy';

  /* ── loading state ── */
  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 240 }}>
      <div style={{
        width: 32, height: 32,
        border: '3px solid var(--green-light)',
        borderTopColor: 'var(--green-primary)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
    </div>
  );

  return (
    <>
      <style>{S}</style>
      <div className="dash-wrap">

        {/* ── Welcome header ── */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ fontFamily: 'Nunito, sans-serif', fontWeight: 900, fontSize: 22, color: 'var(--text-dark)' }}>
              Hello, {user?.name?.split(' ')[0] || 'Partner'} 👋
            </h1>
            <p style={{ fontSize: 13, color: 'var(--text-light)', marginTop: 2 }}>
              {zone ? `${zone.name} (${zone.code})` : 'Set your zone in profile'}
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
            {policy && (
              <span style={{
                display: 'flex', alignItems: 'center', gap: 6, background: 'var(--green-light)',
                border: '1px solid #bbf7d0', color: 'var(--green-dark)', fontSize: 11,
                fontWeight: 700, padding: '5px 12px', borderRadius: 20,
              }}>
                <span style={{ width: 6, height: 6, background: 'var(--green-primary)', borderRadius: '50%', animation: 'pulse 1.5s infinite' }} />
                Covered
              </span>
            )}
            {pollingActive && (
              <span style={{ fontSize: 10, color: 'var(--text-light)' }}>🔄 Live</span>
            )}
          </div>
        </div>

        {/* ── 1. Payout Banner – always top, only when paid ── */}
        {!payoutDismissed && (
          <PayoutBanner payout={latestPayout} onDismiss={() => setPayoutDismissed(true)} />
        )}

        {/* ── 2. Zone Alert – only when backend sends one ── */}
        <ZoneAlertCard alert={zoneAlert} />

        {/* ── 3. Zone Reassignment – only when pending reassignment exists ── */}
        {!reassignDismissed && zoneReassignmentCard && (
          <ZoneReassignmentCard
            card={zoneReassignmentCard}
            onAccept={handleAcceptReassignment}
            onDismiss={handleRejectReassignment}
            processing={reassignProcessing}
          />
        )}

        {/* ── 4. Active Triggers ── */}
        {triggers.length > 0 && (
          <div className="alert-card alert-red">
            <span style={{ fontSize: 22 }}>⚠️</span>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span className="alert-title">Active Disruptions in Your Zone</span>
                <span style={{ marginLeft: 8, background: '#ef4444', color: 'white', fontSize: 10, fontWeight: 800, padding: '2px 7px', borderRadius: 10 }}>
                  {triggers.length}
                </span>
              </div>
              {triggers.map(t => (
                <div key={t.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'white', padding: '10px 14px', borderRadius: '12px', border: '1px solid #e5e7eb', marginTop: '8px' }}>
                  <SourceBadge type={t.trigger_type} severity={t.severity} size="md" />
                </div>
              ))}
              {policy && (
                <p style={{ fontSize: 12, color: '#dc2626', marginTop: 6, fontWeight: 600 }}>
                  ✅ You're covered! Claims will be auto-processed.
                </p>
              )}
            </div>
          </div>
        )}

        {/* ── 5. Coverage Hero Card ── */}
        {policy ? (
          <div className={`policy-hero ${tierClass}`}>
            <p className="policy-hero-label">Active Policy</p>
            <p className="policy-hero-tier">{policy.tier}</p>
            <span className="policy-hero-badge">Active</span>
            <div className="policy-hero-grid">
              <div>
                <p className="policy-hero-stat-label">Daily Payout</p>
                <p className="policy-hero-stat-val">₹{policy.max_daily_payout}</p>
              </div>
              <div>
                <p className="policy-hero-stat-label">Max Days/Wk</p>
                <p className="policy-hero-stat-val">{policy.max_days_per_week}</p>
              </div>
              <div>
                <p className="policy-hero-stat-label">Days Left</p>
                <p className="policy-hero-stat-val">{daysLeft > 0 ? daysLeft : '—'}</p>
              </div>
            </div>
            <div className="policy-hero-footer">
              <div>
                <p className="policy-hero-expires">
                  Expires {new Date(policy.expires_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                </p>
                <p style={{ fontSize: 10, opacity: 0.65, marginTop: 2 }}>
                  Next week: ₹{BASES[policy.tier] || '—'} — zone risk + seasonal included
                </p>
              </div>
              <Link to="/policy"><button className="policy-hero-btn">Details →</button></Link>
            </div>
          </div>
        ) : (
          <div className="rc-card">
            <div className="no-policy-cta">
              <div className="no-policy-icon">🛡️</div>
              <p className="no-policy-title">No Active Policy</p>
              <p className="no-policy-sub">Protect your income from disruptions</p>
              <Link to="/policy" className="rc-btn-primary">Get Coverage</Link>
            </div>
          </div>
        )}

        {/* ── 6. Loyalty Streak ── */}
        <StreakProgressBar loyalty={loyalty} />

        {/* ── 7. Weekly Premium Breakdown ── */}
        <WeeklyPremiumBreakdown breakdown={premiumBreakdown} policy={policy} />

        {/* ── 8. Earnings Summary ── */}
        <div>
          <p className="rc-section-title">Earnings</p>
          <div className="earn-grid">
            <div className="earn-tile">
              <p className="earn-label">Total Received</p>
              <p className="earn-amount" style={{ color: 'var(--green-dark)' }}>₹{summary?.total_paid || 0}</p>
              <p className="earn-claims">{summary?.total_claims || 0} claims</p>
            </div>
            <div className="earn-tile">
              <p className="earn-label">Pending</p>
              <p className="earn-amount" style={{ color: '#f97316' }}>₹{summary?.pending_amount || 0}</p>
              <p className="earn-claims">{summary?.pending_claims || 0} claims</p>
            </div>
          </div>
        </div>

        {/* ── 9. Recent Claims ── */}
        {recentClaims.length > 0 && (
          <div className="rc-card">
            <div className="rc-card-body">
              <div className="sec-hdr">
                <span className="rc-section-title" style={{ marginBottom: 0 }}>Recent Claims</span>
                <Link to="/claims" className="sec-hdr-link">View All →</Link>
              </div>
              {recentClaims.map(claim => (
                <div className="claim-row" key={claim.id}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <SourceBadge type={claim.trigger_type} showLabel={false} size="lg" />
                    <div>
                      <p className="claim-label" style={{textTransform: 'capitalize'}}>{claim.trigger_type}</p>
                      <p className="claim-date">
                        {new Date(claim.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                      </p>
                    </div>
                  </div>
                  <div>
                    <p className="claim-amount">₹{claim.amount}</p>
                    <span className={`claim-status ${STATUS_CLS[claim.status] || 'st-pending'}`}>{claim.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── 10. Quick Actions ── */}
        <div>
          <p className="rc-section-title">Quick Actions</p>
          <div className="qa-grid">
            <Link to="/policy" className="qa-tile">
              <div className="qa-tile-icon">📋</div>
              <p className="qa-tile-label">View Policy</p>
            </Link>
            <Link to="/claims" className="qa-tile">
              <div className="qa-tile-icon">💰</div>
              <p className="qa-tile-label">Claim History</p>
            </Link>
          </div>
        </div>

        {/* ── 11. Coverage events ── */}
        <div className="rc-card">
          <div className="rc-card-body">
            <p className="rc-section-title">You're covered for:</p>
            {COV_EVENTS.map(e => (
              <div className="cov-row" key={e.label}>
                <span style={{ fontSize: 18 }}>{e.icon}</span>
                <span>{e.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div style={{ background: '#fef2f2', border: '1.5px solid #fecaca', borderRadius: 16, padding: '14px 16px', color: '#dc2626', fontSize: 13 }}>
            {error}
          </div>
        )}

      </div>
    </>
  );
}

export default Dashboard;