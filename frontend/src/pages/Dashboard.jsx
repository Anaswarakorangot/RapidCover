import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

/* ─── Design Tokens (matches Register.jsx UI) ─────────────────────────────── */
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
  .policy-hero.flex-tier    { background: linear-gradient(135deg, #059669, #10b981); }
  .policy-hero.standard-tier{ background: linear-gradient(135deg, #2563eb, #3b82f6); }
  .policy-hero.pro-tier     { background: linear-gradient(135deg, #7c3aed, #8b5cf6); }
  .policy-hero.no-policy    { background: linear-gradient(135deg, #6b7280, #9ca3af); }

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
  .alert-title  { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 13px; }
  .alert-orange .alert-title { color: #9a3412; }
  .alert-blue   .alert-title { color: #1e40af; }
  .alert-red    .alert-title { color: #991b1b; }
  .alert-body   { font-size: 12px; margin-top: 2px; line-height: 1.5; }
  .alert-orange .alert-body { color: #c2410c; }
  .alert-blue   .alert-body { color: #1d4ed8; }
  .alert-red    .alert-body { color: #dc2626; }

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
  .qa-tile-icon { font-size: 24px; }
  .qa-tile-label { font-size: 12px; font-weight: 600; color: var(--text-dark); margin-top: 6px; font-family: 'Nunito', sans-serif; }

  /* ── Earnings tiles ── */
  .earn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .earn-tile { background: var(--white); border: 1.5px solid var(--border); border-radius: 18px; padding: 16px; text-align: center; }
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
  .no-policy-cta {
    text-align: center; padding: 28px 16px;
  }
  .no-policy-icon { font-size: 48px; }
  .no-policy-title { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 18px; color: var(--text-dark); margin: 10px 0 6px; }
  .no-policy-sub { font-size: 13px; color: var(--text-mid); margin-bottom: 18px; }
  .rc-btn-primary {
    display: inline-block; background: var(--green-primary); color: white;
    border: none; border-radius: 14px; padding: 13px 28px; font-family: 'Nunito', sans-serif;
    font-weight: 800; font-size: 15px; cursor: pointer; text-decoration: none;
    transition: background 0.2s;
  }
  .rc-btn-primary:hover { background: var(--green-dark); }
`;

/* ─── Sub-components ──────────────────────────────────────────────────────── */

function ZoneReassignmentCard({ notification, onAccept, onDismiss }) {
  if (!notification) return null;
  const { oldZone, newZone, premiumDelta, hoursLeft } = notification;
  return (
    <div className="alert-card alert-orange">
      <span style={{ fontSize: 22 }}>📍</span>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span className="alert-title">Zone Reassignment</span>
          <span className="alert-badge">{hoursLeft}h to accept</span>
        </div>
        <p className="alert-body">
          Zepto reassigned your zone from <strong>{oldZone}</strong> to <strong>{newZone}</strong>.
          {premiumDelta !== 0 && (
            <span style={{ color: premiumDelta > 0 ? '#c2410c' : '#166534' }}>
              {' '}Premium {premiumDelta > 0 ? `+₹${premiumDelta}` : `-₹${Math.abs(premiumDelta)}`}/week.
            </span>
          )}
        </p>
        <div className="alert-actions">
          <button className="alert-btn-outline" onClick={onDismiss}>Decline</button>
          <button className="alert-btn-fill" onClick={onAccept}>Accept New Zone</button>
        </div>
      </div>
    </div>
  );
}

function WeatherAlertCard({ alert }) {
  if (!alert) return null;
  return (
    <div className="alert-card alert-blue">
      <span style={{ fontSize: 22 }}>🌧️</span>
      <div>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span className="alert-title">48-Hour Weather Alert</span>
          <span className="alert-badge">Heads up</span>
        </div>
        <p className="alert-body">{alert.message}</p>
        <p style={{ fontSize: 11, color: '#3b82f6', marginTop: 4 }}>Keep your documents handy for quick claims.</p>
      </div>
    </div>
  );
}

function StreakProgressBar({ streakWeeks }) {
  const w4 = Math.min((streakWeeks / 4) * 100, 100);
  const w12 = Math.min((streakWeeks / 12) * 100, 100);
  const done4 = streakWeeks >= 4;
  const done12 = streakWeeks >= 12;

  return (
    <div className="rc-card">
      <div className="rc-card-body">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <span className="rc-section-title" style={{ marginBottom: 0 }}>🔥 Loyalty Streak</span>
          <span style={{ fontSize: 12, color: 'var(--text-light)', fontWeight: 600 }}>{streakWeeks} week{streakWeeks !== 1 ? 's' : ''} active</span>
        </div>
        <div className="streak-bar-wrap">
          <div className="streak-bar-header">
            <span className="streak-bar-label">{done4 ? '✅' : '🎯'} 4-week milestone (6% off)</span>
            <span className="streak-bar-val" style={{ color: done4 ? '#22c55e' : 'var(--text-mid)' }}>
              {done4 ? 'Unlocked!' : `${streakWeeks}/4 wks`}
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
              {done12 ? 'Unlocked!' : `${streakWeeks}/12 wks`}
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

function WeeklyPremiumBreakdown({ policy }) {
  const today = new Date();
  const isMonday = today.getDay() === 1;
  const [open, setOpen] = useState(isMonday);

  if (!policy) return null;

  const BASES = { flex: 22, standard: 33, pro: 45 };
  const base = BASES[policy.tier] || 33;
  const zoneRisk = 3;
  const seasonal = 1.15;
  const riqi = 1.15;
  const activity = policy.tier === 'pro' ? 1.35 : policy.tier === 'flex' ? 0.80 : 1.00;
  const loyalty = 0.94;
  const fee = 0;
  const total = Math.round(base * activity * riqi * seasonal * loyalty + zoneRisk + fee);

  const rows = [
    { label: 'Base Premium', note: `${policy.tier} plan`, val: `₹${base}`, cls: '' },
    { label: 'Zone Risk Factor', note: 'Urban Core surcharge', val: `+₹${zoneRisk}`, cls: 'positive' },
    { label: 'Seasonal Index', note: 'City-specific monthly', val: `×${seasonal.toFixed(2)}`, cls: '' },
    { label: 'RIQI Adjustment', note: 'Urban Fringe band', val: `×${riqi.toFixed(2)}`, cls: 'positive' },
    { label: 'Activity Tier Factor', note: policy.tier, val: `×${activity.toFixed(2)}`, cls: '' },
    { label: 'Loyalty Discount', note: '4-week streak', val: `×${loyalty.toFixed(2)}`, cls: 'negative' },
    { label: 'Platform Fee', note: 'Waived', val: '₹0', cls: '' },
  ];

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
                <span className="breakdown-key">{r.label}<span className="breakdown-note">({r.note})</span></span>
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
  const [policy, setPolicy] = useState(null);
  const [summary, setSummary] = useState(null);
  const [zone, setZone] = useState(null);
  const [triggers, setTriggers] = useState([]);
  const [recentClaims, setRecentClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showZoneCard, setShowZoneCard] = useState(true);

  const zoneReassignment = { oldZone: 'Kondapur Central', newZone: 'Gachibowli West', premiumDelta: 3, hoursLeft: 18 };
  const weatherAlert = { message: 'Heavy rain forecast Tuesday 4PM in your zone. Stay prepared.' };
  const streakWeeks = 3;

  useEffect(() => {
    async function load() {
      try {
        const [pol, summ, claims] = await Promise.all([
          api.getActivePolicy().catch(() => null),
          api.getClaimsSummary(),
          api.getClaims(1, 3).catch(() => ({ claims: [] })),
        ]);
        setPolicy(pol); setSummary(summ); setRecentClaims(claims.claims || []);
        if (user?.zone_id) {
          const z = await api.getZone(user.zone_id).catch(() => null);
          const tr = await api.getActiveTriggers(user.zone_id).catch(() => ({ triggers: [] }));
          setZone(z); setTriggers(tr.triggers || []);
        }
      } catch (e) { console.error(e); } finally { setLoading(false); }
    }
    load();
  }, [user?.zone_id]);

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 240 }}>
      <div style={{ width: 32, height: 32, border: '3px solid var(--green-light)', borderTopColor: 'var(--green-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
    </div>
  );

  const BASES = { flex: 22, standard: 33, pro: 45 };
  const daysLeft = policy ? Math.ceil((new Date(policy.expires_at) - new Date()) / 864e5) : 0;
  const tierClass = { flex: 'flex-tier', standard: 'standard-tier', pro: 'pro-tier' }[policy?.tier] || 'no-policy';

  const TRIGGER_INFO = {
    rain: { icon: '🌧️', label: 'Heavy Rain', color: '#eff6ff', border: '#bfdbfe', text: '#1e40af' },
    heat: { icon: '🌡️', label: 'Extreme Heat', color: '#fef2f2', border: '#fecaca', text: '#991b1b' },
    aqi: { icon: '💨', label: 'Dangerous AQI', color: '#fffbeb', border: '#fde68a', text: '#92400e' },
    shutdown: { icon: '🚫', label: 'Civic Shutdown', color: '#faf5ff', border: '#e9d5ff', text: '#6b21a8' },
    closure: { icon: '🏪', label: 'Store Closure', color: '#f9fafb', border: '#e5e7eb', text: '#374151' },
  };
  const STATUS_CLS = { paid: 'st-paid', pending: 'st-pending', approved: 'st-approved', rejected: 'st-rejected' };
  const COV_EVENTS = [
    { icon: '🌧️', label: 'Heavy Rain & Floods' },
    { icon: '🌡️', label: 'Extreme Heat (>43°C)' },
    { icon: '💨', label: 'Dangerous AQI (>400)' },
    { icon: '🚫', label: 'Curfew & Bandh' },
    { icon: '🏪', label: 'Dark Store Closures' },
  ];

  return (
    <>
      <style>{S}</style>
      <div className="dash-wrap">

        {/* ── Welcome header ── */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ fontFamily: 'Nunito, sans-serif', fontWeight: 900, fontSize: 22, color: 'var(--text-dark)' }}>
              Hello, {user?.name?.split(' ')[0]} 👋
            </h1>
            <p style={{ fontSize: 13, color: 'var(--text-light)', marginTop: 2 }}>
              {zone ? `${zone.name} (${zone.code})` : 'Set your zone in profile'}
            </p>
          </div>
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
        </div>

        {/* ── Zone Reassignment ── */}
        {showZoneCard && (
          <ZoneReassignmentCard
            notification={zoneReassignment}
            onAccept={() => setShowZoneCard(false)}
            onDismiss={() => setShowZoneCard(false)}
          />
        )}

        {/* ── 48h Weather Alert ── */}
        <WeatherAlertCard alert={weatherAlert} />

        {/* ── Active Triggers ── */}
        {triggers.length > 0 && (
          <div className="alert-card alert-red">
            <span style={{ fontSize: 22 }}>⚠️</span>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span className="alert-title">Active Disruptions in Your Zone</span>
                <span style={{ marginLeft: 8, background: '#ef4444', color: 'white', fontSize: 10, fontWeight: 800, padding: '2px 7px', borderRadius: 10 }}>{triggers.length}</span>
              </div>
              {triggers.map(t => {
                const info = TRIGGER_INFO[t.trigger_type] || { icon: '⚠️', label: t.trigger_type, color: '#f9fafb', border: '#e5e7eb', text: '#374151' };
                return (
                  <div key={t.id} className="trigger-chip" style={{ background: info.color, borderColor: info.border, color: info.text, marginTop: 8 }}>
                    <span>{info.icon} <strong>{info.label}</strong></span>
                    <span style={{ fontSize: 11, fontWeight: 700 }}>Severity {t.severity}/5</span>
                  </div>
                );
              })}
              {policy && <p style={{ fontSize: 12, color: '#dc2626', marginTop: 6, fontWeight: 600 }}>✅ You're covered! Claims will be auto-processed.</p>}
            </div>
          </div>
        )}

        {/* ── Coverage Hero Card ── */}
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

        {/* ── Streak Counter ── */}
        <StreakProgressBar streakWeeks={streakWeeks} />

        {/* ── Weekly Premium Breakdown ── */}
        <WeeklyPremiumBreakdown policy={policy} />

        {/* ── Earnings Summary ── */}
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

        {/* ── Recent Claims ── */}
        {recentClaims.length > 0 && (
          <div className="rc-card">
            <div className="rc-card-body">
              <div className="sec-hdr">
                <span className="rc-section-title" style={{ marginBottom: 0 }}>Recent Claims</span>
                <Link to="/claims" className="sec-hdr-link">View All →</Link>
              </div>
              {recentClaims.map(claim => {
                const info = TRIGGER_INFO[claim.trigger_type] || { icon: '📋', label: claim.trigger_type };
                return (
                  <div className="claim-row" key={claim.id}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span style={{ fontSize: 24 }}>{info.icon}</span>
                      <div>
                        <p className="claim-label">{info.label}</p>
                        <p className="claim-date">{new Date(claim.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</p>
                      </div>
                    </div>
                    <div>
                      <p className="claim-amount">₹{claim.amount}</p>
                      <span className={`claim-status ${STATUS_CLS[claim.status] || 'st-pending'}`}>{claim.status}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Quick Actions ── */}
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

        {/* ── Coverage events ── */}
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

      </div>
    </>
  );
}