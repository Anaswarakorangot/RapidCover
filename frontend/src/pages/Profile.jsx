/**
 * Profile.jsx  –  Partner profile, zone history, renewal preview
 *
 * Person 1 Phase 2:
 *   - Removed MOCK_ZONE_HISTORY constant
 *   - Removed hardcoded renewal premium breakdown
 *   - Zone history from GET /partners/me/zone-history
 *   - Renewal preview from GET /partners/me/renewal-preview
 *   - Empty state shown when no zone history exists
 *   - "Zone #id" chip replaced with actual zone name/code/city when available
 *
 * UI: Original green theme restored (matching Login.jsx / Register.jsx).
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { NotificationToggle } from '../components/NotificationToggle';
import { UpiSelector } from '../components/ui/UpiSelector';
import RapidBot from '../components/RapidBot';
import PrivacyConsentPanel from '../components/PrivacyConsentPanel';
import api from '../services/api';

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

  .prf-wrap {
    font-family: 'DM Sans', sans-serif;
    color: var(--text-dark);
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-bottom: 40px;
  }

  /* ── Shared card ── */
  .prf-card {
    background: var(--white);
    border-radius: 20px;
    border: 1.5px solid var(--border);
    overflow: hidden;
  }
  .prf-card-body { padding: 18px; }

  /* ── Section title ── */
  .prf-section-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    font-size: 14px;
    color: var(--text-dark);
    margin-bottom: 4px;
  }
  .prf-section-sub { font-size: 11.5px; color: var(--text-light); margin-bottom: 12px; }

  /* ── Avatar hero ── */
  .prf-hero {
    background: linear-gradient(135deg, var(--green-primary), var(--green-dark));
    border-radius: 20px;
    padding: 24px 18px;
    display: flex;
    align-items: center;
    gap: 16px;
    color: white;
  }
  .prf-avatar {
    width: 60px; height: 60px; border-radius: 50%;
    background: rgba(255,255,255,0.25);
    display: flex; align-items: center; justify-content: center;
    font-size: 28px; flex-shrink: 0;
    border: 2px solid rgba(255,255,255,0.4);
  }
  .prf-hero-name   { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 18px; }
  .prf-hero-phone  { font-size: 13px; opacity: 0.8; margin-top: 2px; }
  .prf-hero-plat   { font-size: 11px; opacity: 0.65; margin-top: 1px; text-transform: capitalize; }

  /* ── Inline input ── */
  .prf-input {
    width: 100%;
    padding: 12px 14px;
    border: 1.5px solid var(--border);
    border-radius: 13px;
    font-size: 14px;
    font-family: 'DM Sans', sans-serif;
    background: var(--gray-bg);
    outline: none;
    color: var(--text-dark);
    transition: border-color 0.2s, box-shadow 0.2s;
    box-sizing: border-box;
  }
  .prf-input:focus {
    border-color: var(--green-primary);
    box-shadow: 0 0 0 3px rgba(61,184,92,0.12);
    background: var(--white);
  }
  .prf-input.valid   { border-color: var(--green-primary); }
  .prf-input.invalid { border-color: var(--warning); }

  .prf-label {
    font-family: 'Nunito', sans-serif;
    font-size: 12.5px; font-weight: 700; color: var(--text-dark);
    display: block; margin-bottom: 6px;
  }
  .prf-hint { font-size: 11.5px; color: var(--text-light); margin-top: 4px; }
  .prf-hint.warn { color: var(--warning); }

  .prf-field { margin-bottom: 14px; }
  .prf-input-wrap { position: relative; }
  .prf-input-icon {
    position: absolute; right: 12px; top: 50%;
    transform: translateY(-50%); font-size: 14px;
  }

  /* ── Buttons ── */
  .prf-btn-primary {
    background: var(--green-primary); color: white; border: none;
    border-radius: 13px; padding: 13px; width: 100%;
    font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 15px;
    cursor: pointer; transition: background 0.2s;
  }
  .prf-btn-primary:hover { background: var(--green-dark); }
  .prf-btn-primary:disabled { background: var(--border); cursor: not-allowed; }

  .prf-btn-outline {
    background: transparent; color: var(--text-dark);
    border: 1.5px solid var(--border); border-radius: 13px; padding: 10px 16px;
    font-family: 'DM Sans', sans-serif; font-weight: 600; font-size: 13px;
    cursor: pointer; transition: border-color 0.2s;
  }
  .prf-btn-outline:hover { border-color: var(--green-primary); color: var(--green-dark); }

  .prf-btn-secondary {
    background: var(--gray-bg); color: var(--text-mid); border: 1.5px solid var(--border);
    border-radius: 13px; padding: 11px; font-family: 'DM Sans', sans-serif;
    font-weight: 600; font-size: 14px; cursor: pointer;
  }

  .prf-btn-danger {
    background: transparent; color: var(--error); border: 1.5px solid #fecaca;
    border-radius: 13px; padding: 13px; width: 100%;
    font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 15px;
    cursor: pointer;
  }

  .prf-btn-row { display: flex; gap: 8px; }

  /* ── Select ── */
  .prf-select {
    width: 100%; padding: 12px 14px; border: 1.5px solid var(--border);
    border-radius: 13px; font-size: 14px; font-family: 'DM Sans', sans-serif;
    background: var(--gray-bg); outline: none; color: var(--text-dark);
    appearance: none; -webkit-appearance: none;
  }

  /* ── KYC status badges ── */
  .kyc-badge {
    font-size: 12px; font-weight: 700; padding: 4px 12px;
    border-radius: 10px; display: inline-block;
  }
  .kyc-verified  { background: var(--green-light); color: var(--green-dark); }
  .kyc-pending   { background: #fef3c7; color: #92400e; }
  .kyc-failed    { background: #fef2f2; color: var(--error); }
  .kyc-skipped   { background: var(--gray-bg); color: var(--text-light); }

  /* ── Zone history ── */
  .zh-item {
    border: 1.5px solid var(--border); border-radius: 14px;
    padding: 12px 14px; background: var(--gray-bg); margin-bottom: 10px;
  }
  .zh-item:last-child { margin-bottom: 0; }
  .zh-meta { display: flex; justify-content: space-between; margin-bottom: 6px; }
  .zh-date   { font-size: 12px; font-weight: 700; color: var(--text-dark); }
  .zh-reason { font-size: 11px; color: var(--text-light); }
  .zh-zones  { display: flex; align-items: center; gap: 8px; font-size: 13px; }
  .zh-old    { color: var(--text-mid); }
  .zh-arrow  { color: var(--text-light); }
  .zh-new    { font-weight: 700; color: var(--text-dark); }
  .zh-premium { display: flex; align-items: center; gap: 6px; margin-top: 5px; font-size: 12px; }
  .zh-prem-label { color: var(--text-light); }
  .zh-prem-old   { color: var(--text-mid); }
  .zh-prem-new.up   { color: #f97316; font-weight: 700; }
  .zh-prem-new.down { color: var(--green-dark); font-weight: 700; }

  /* ── Renewal breakdown ── */
  .ren-row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 13px; }
  .ren-key  { color: var(--text-mid); }
  .ren-note { font-size: 10.5px; color: var(--text-light); margin-left: 4px; }
  .ren-val  { font-weight: 600; color: var(--text-dark); }
  .ren-val.neg { color: var(--green-dark); }
  .ren-total {
    border-top: 1.5px solid var(--border); padding-top: 10px; margin-top: 6px;
    display: flex; justify-content: space-between;
    font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 16px;
  }
  .ren-total .val { color: var(--green-dark); }

  /* ── Action links ── */
  .prf-action-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 11px 0; border-bottom: 1px solid var(--border);
    font-size: 13px; color: var(--text-mid); cursor: pointer;
    background: none; border-left: none; border-right: none; border-top: none;
    width: 100%; text-align: left; font-family: 'DM Sans', sans-serif;
  }
  .prf-action-row:last-child { border-bottom: none; }
  .prf-action-row:hover { color: var(--text-dark); }

  /* ── Zone info chip ── */
  .zone-chip {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--green-light); color: var(--green-dark);
    font-size: 13px; font-weight: 700; padding: 6px 14px;
    border-radius: 20px; margin-top: 4px;
  }

  /* ── File upload area ── */
  .prf-file-label {
    display: flex; align-items: center; gap: 10px;
    padding: 12px 14px; border: 1.5px dashed var(--border);
    border-radius: 13px; background: var(--gray-bg);
    cursor: pointer; font-size: 13px; color: var(--text-mid);
    transition: border-color 0.2s;
  }
  .prf-file-label.has-file { border-color: var(--green-primary); background: var(--green-light); color: var(--green-dark); }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Legal Modal ── */
  .legal-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.4); backdrop-filter: blur(4px);
    z-index: 2000; display: flex; align-items: flex-end;
  }
  .legal-sheet {
    background: white; width: 100%; max-height: 85vh;
    border-radius: 24px 24px 0 0; padding: 24px;
    display: flex; flex-direction: column; gap: 16px;
    animation: slideUp 0.3s ease-out; overflow-y: auto;
  }
  @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
  
  .legal-title { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 20px; }
  .legal-body  { font-size: 14px; line-height: 1.6; color: var(--text-mid); }
  .legal-section { margin-bottom: 20px; }
  .legal-h3 { font-weight: 700; color: var(--text-dark); margin-bottom: 8px; font-size: 15px; }
  
  .support-card {
    background: var(--green-light); border-radius: 16px; padding: 16px;
    display: flex; align-items: center; gap: 12px; border: 1px solid var(--green-primary);
    text-decoration: none; color: var(--green-dark); font-weight: 700;
  }
  .grok-card {
    background: #1a2e1a; border-radius: 16px; padding: 18px;
    display: flex; align-items: center; gap: 14px; border: 1.5px solid rgba(61, 184, 92, 0.3);
    cursor: pointer; color: #fff; font-weight: 700;
    transition: transform 0.2s, border-color 0.2s;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
  }
  .grok-card:active { transform: scale(0.97); }
  .grok-card:hover { border-color: var(--green-primary); }
`;

/* ─── LANGUAGES ─────────────────────────────────────────────────────────── */
const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी (Hindi)' },
  { code: 'ta', label: 'தமிழ் (Tamil)' },
  { code: 'kn', label: 'ಕನ್ನಡ (Kannada)' },
  { code: 'te', label: 'తెలుగు (Telugu)' },
  { code: 'mr', label: 'मराठी (Marathi)' },
  { code: 'bn', label: 'বাংলা (Bengali)' },
];

function validateUPI(v) { return /^[\w.\-]{3,}@[\w]{3,}$/.test(v.trim()); }
function validateAadhaar(v) { return /^\d{12}$/.test(v.replace(/\s/g, '')); }
function validatePAN(v) { return /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(v.trim().toUpperCase()); }

/* ─── UpiSetup ──────────────────────────────────────────────────────────── */
function UpiSetup({ currentUpiId, onSave }) {
  const [editing, setEditing] = useState(false);
  const [upiId, setUpiId] = useState(currentUpiId || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const valid = upiId.trim() ? validateUPI(upiId) : null;

  async function save() {
    if (!valid) { setError('Invalid UPI ID format'); return; }
    setSaving(true); setError('');
    try {
      await api.updateProfile({ upi_id: upiId.trim() });
      onSave?.(upiId.trim()); setEditing(false);
    } catch (e) { setError(e.message); } finally { setSaving(false); }
  }

  if (!editing) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
      <div>
        {currentUpiId
          ? <><p style={{ fontWeight: 700, fontSize: 14 }}>{currentUpiId}</p><p style={{ fontSize: 12, color: 'var(--green-primary)', marginTop: 2 }}>✓ UPI linked</p></>
          : <p style={{ fontSize: 13, color: 'var(--text-light)', fontStyle: 'italic' }}>No UPI ID linked yet</p>
        }
      </div>
      <button className="prf-btn-outline" onClick={() => setEditing(true)}>{currentUpiId ? 'Change' : 'Add UPI'}</button>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <UpiSelector 
        value={upiId}
        onChange={v => { setUpiId(v); setError(''); }}
      />
      {error && <p style={{ fontSize: 12, color: 'var(--error)', background: '#fef2f2', padding: '6px 10px', borderRadius: 8 }}>{error}</p>}
      <div className="prf-btn-row">
        <button className="prf-btn-secondary" style={{ flex: 1 }} onClick={() => { setEditing(false); setUpiId(currentUpiId || ''); setError(''); }}>Cancel</button>
        <button className="prf-btn-primary" style={{ flex: 2 }} onClick={save} disabled={!valid || saving}>
          {saving ? 'Saving…' : 'Save UPI'}
        </button>
      </div>
    </div>
  );
}

/* ─── KycSetup ──────────────────────────────────────────────────────────── */
function KycSetup({ currentKyc, onSave }) {
  const [editing, setEditing] = useState(false);
  const [aadhaar, setAadhaar] = useState(currentKyc?.aadhaar_number || '');
  const [pan, setPan] = useState(currentKyc?.pan_number || '');
  const [aadhaarFile, setAadhaarFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const av = aadhaar.trim() ? validateAadhaar(aadhaar) : null;
  const pv = pan.trim() ? validatePAN(pan) : null;

  const st = currentKyc?.kyc_status || 'skipped';
  const ST_MAP = {
    verified: { label: '✓ KYC Verified', cls: 'kyc-verified' },
    pending:  { label: '⏳ KYC Pending Review', cls: 'kyc-pending' },
    failed:   { label: '✗ KYC Failed', cls: 'kyc-failed' },
    skipped:  { label: 'KYC not submitted', cls: 'kyc-skipped' },
  };
  const badge = ST_MAP[st] || ST_MAP.skipped;

  async function save() {
    if (aadhaar && !validateAadhaar(aadhaar)) { setError('Aadhaar must be 12 digits'); return; }
    if (pan && !validatePAN(pan)) { setError('Invalid PAN format (e.g. ABCDE1234F)'); return; }
    setSaving(true); setError('');
    try {
      await api.updateProfile({
        kyc: {
          aadhaar_number: aadhaar.replace(/\s/g, '') || null,
          pan_number: pan.toUpperCase() || null,
          kyc_status: aadhaar ? 'pending' : 'skipped',
        }
      });
      onSave?.({ aadhaar_number: aadhaar, pan_number: pan, kyc_status: aadhaar ? 'pending' : 'skipped' });
      setEditing(false);
    } catch (e) { setError(e.message); } finally { setSaving(false); }
  }

  if (!editing) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className={`kyc-badge ${badge.cls}`}>{badge.label}</span>
        <button className="prf-btn-outline" onClick={() => setEditing(true)}>
          {st === 'skipped' ? 'Add KYC' : 'Update'}
        </button>
      </div>
      {currentKyc?.aadhaar_number && <p style={{ fontSize: 13, color: 'var(--text-mid)' }}>Aadhaar: ••••  ••••  {currentKyc.aadhaar_number.slice(-4)}</p>}
      {currentKyc?.pan_number && <p style={{ fontSize: 13, color: 'var(--text-mid)' }}>PAN: {currentKyc.pan_number}</p>}
      <p style={{ fontSize: 11, color: 'var(--text-light)' }}>🔒 Mock KYC — no real data stored</p>
    </div>
  );

  const inp = (v) => ({ className: `prf-input${v === true ? ' valid' : v === false ? ' invalid' : ''}` });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <p style={{ fontSize: 12, background: '#fff8e1', border: '1px solid #fde68a', borderRadius: 8, padding: '6px 10px', color: '#92400e' }}>
        🔒 Mock KYC — fields are for demo only
      </p>
      <div className="prf-field">
        <label className="prf-label">Aadhaar Number <span style={{ fontWeight: 400, color: 'var(--text-light)' }}>(optional)</span></label>
        <div className="prf-input-wrap">
          <input {...inp(av)} placeholder="1234 5678 9012" maxLength={14} value={aadhaar} onChange={e => { setAadhaar(e.target.value); setError(''); }} />
          {av !== null && <span className="prf-input-icon" style={{ color: av ? 'var(--green-primary)' : 'var(--warning)' }}>{av ? '✓' : '✗'}</span>}
        </div>
        <p className={`prf-hint${av === false ? ' warn' : ''}`}>{av === false ? 'Must be 12 digits' : '12-digit Aadhaar number'}</p>
      </div>
      <div className="prf-field">
        <label className="prf-label">PAN Number <span style={{ fontWeight: 400, color: 'var(--text-light)' }}>(optional)</span></label>
        <div className="prf-input-wrap">
          <input {...inp(pv)} placeholder="ABCDE1234F" maxLength={10} value={pan} onChange={e => { setPan(e.target.value.toUpperCase()); setError(''); }} />
          {pv !== null && <span className="prf-input-icon" style={{ color: pv ? 'var(--green-primary)' : 'var(--warning)' }}>{pv ? '✓' : '✗'}</span>}
        </div>
        <p className={`prf-hint${pv === false ? ' warn' : ''}`}>{pv === false ? 'Format: ABCDE1234F' : 'e.g. ABCDE1234F'}</p>
      </div>
      <div className="prf-field">
        <label className="prf-label">Upload Aadhaar <span style={{ fontWeight: 400, color: 'var(--text-light)' }}>(optional)</span></label>
        <label htmlFor="prf-aadhaar-file" className={`prf-file-label${aadhaarFile ? ' has-file' : ''}`}>
          <span>{aadhaarFile ? '✅' : '📎'}</span>
          <span>{aadhaarFile ? aadhaarFile.name : 'Tap to upload Aadhaar (image/PDF)'}</span>
        </label>
        <input id="prf-aadhaar-file" type="file" accept="image/*,.pdf" style={{ display: 'none' }} onChange={e => setAadhaarFile(e.target.files[0] || null)} />
        <p className="prf-hint">JPEG, PNG or PDF · Mock upload</p>
      </div>
      {error && <p style={{ fontSize: 12, color: 'var(--error)', background: '#fef2f2', padding: '6px 10px', borderRadius: 8 }}>{error}</p>}
      <div className="prf-btn-row">
        <button className="prf-btn-secondary" style={{ flex: 1 }} onClick={() => { setEditing(false); setError(''); }}>Cancel</button>
        <button className="prf-btn-primary" style={{ flex: 2 }} onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save KYC'}</button>
      </div>
    </div>
  );
}

/* ─── BankSetup ─────────────────────────────────────────────────────────── */
function BankSetup({ partner, onSave }) {
  const [editing, setEditing] = useState(false);
  const [bankName, setBankName] = useState(partner?.bank_name || '');
  const [accNum, setAccNum] = useState(partner?.account_number || '');
  const [ifsc, setIfsc] = useState(partner?.ifsc_code || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function save() {
    setSaving(true); setError('');
    try {
      await api.updateProfile({ 
        bank_name: bankName.trim(), 
        account_number: accNum.trim(),
        ifsc_code: ifsc.trim().toUpperCase()
      });
      onSave?.({ bank_name: bankName, account_number: accNum, ifsc_code: ifsc });
      setEditing(false);
    } catch (e) { setError(e.message); } finally { setSaving(false); }
  }

  if (!editing) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
      <div>
        {partner?.bank_name 
          ? <><p style={{ fontWeight: 700, fontSize: 14 }}>{partner.bank_name}</p><p style={{ fontSize: 12, color: 'var(--green-primary)', marginTop: 2 }}>✓ Account ****{partner.account_number?.slice(-4)}</p></>
          : <p style={{ fontSize: 13, color: 'var(--text-light)', fontStyle: 'italic' }}>No bank account linked yet</p>
        }
      </div>
      <button className="prf-btn-outline" onClick={() => setEditing(true)}>{partner?.bank_name ? 'Update' : 'Setup Bank'}</button>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="prf-field">
        <label className="prf-label">Bank Name</label>
        <input className="prf-input" value={bankName} onChange={e => setBankName(e.target.value)} placeholder="e.g. HDFC Bank" />
      </div>
      <div className="prf-field">
        <label className="prf-label">Account Number</label>
        <input className="prf-input" value={accNum} onChange={e => setAccNum(e.target.value)} placeholder="Full account number" />
      </div>
      <div className="prf-field">
        <label className="prf-label">IFSC Code</label>
        <input className="prf-input" value={ifsc} onChange={e => setIfsc(e.target.value.toUpperCase())} placeholder="HDFC0001234" maxLength={11} />
      </div>
      {error && <p style={{ fontSize: 12, color: 'var(--error)', background: '#fef2f2', padding: '6px 10px', borderRadius: 8 }}>{error}</p>}
      <div className="prf-btn-row">
        <button className="prf-btn-secondary" style={{ flex: 1 }} onClick={() => setEditing(false)}>Cancel</button>
        <button className="prf-btn-primary" style={{ flex: 2 }} onClick={save} disabled={saving}>{saving ? 'Saving...' : 'Save Bank Details'}</button>
      </div>
    </div>
  );
}

/* ─── ZoneHistorySection – real data from backend ────────────────────────── */
function ZoneHistorySection({ zoneHistoryData, loading }) {
  const [open, setOpen] = useState(false);

  const history = zoneHistoryData?.history || [];
  const hasHistory = zoneHistoryData?.has_history && history.length > 0;

  return (
    <div className="prf-card">
      <div className="prf-card-body">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <p className="prf-section-title" style={{ marginBottom: 0 }}>📍 Zone Reassignment History</p>
          {hasHistory && (
            <button
              style={{ fontSize: 11, fontWeight: 700, color: 'var(--green-dark)', background: 'var(--green-light)', border: 'none', borderRadius: 20, padding: '4px 12px', cursor: 'pointer' }}
              onClick={() => setOpen(v => !v)}
            >
              {open ? 'Hide' : `Show (${history.length})`}
            </button>
          )}
        </div>

        {loading ? (
          <p style={{ fontSize: 13, color: 'var(--text-light)' }}>Loading history…</p>
        ) : !hasHistory ? (
          <p style={{ fontSize: 13, color: 'var(--text-light)' }}>No zone changes yet.</p>
        ) : !open ? (
          <p style={{ fontSize: 13, color: 'var(--text-light)' }}>
            {history.length} past zone change{history.length !== 1 ? 's' : ''} on record.
          </p>
        ) : history.map((h, i) => {
          const oldZone = h.old_zone_name || h.oldZone || '—';
          const newZone = h.new_zone_name || h.newZone || '—';
          const premBefore = h.premium_before ?? h.premiumBefore;
          const premAfter  = h.premium_after  ?? h.premiumAfter;
          const reason     = h.reason || h.reassignment_reason || '';
          const dateStr    = h.effective_at || h.date;
          const up = premAfter > premBefore;
          const delta = Math.abs((premAfter || 0) - (premBefore || 0));

          return (
            <div className="zh-item" key={i}>
              <div className="zh-meta">
                <span className="zh-date">
                  {dateStr ? new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : '—'}
                </span>
                {reason && <span className="zh-reason">{reason}</span>}
              </div>
              <div className="zh-zones">
                <span className="zh-old">{oldZone}</span>
                <span className="zh-arrow">→</span>
                <span className="zh-new">{newZone}</span>
              </div>
              {premBefore != null && premAfter != null && (
                <div className="zh-premium">
                  <span className="zh-prem-label">Premium:</span>
                  <span className="zh-prem-old">₹{premBefore}</span>
                  <span className="zh-arrow">→</span>
                  <span className={`zh-prem-new ${up ? 'up' : 'down'}`}>
                    ₹{premAfter}/wk ({up ? `+₹${delta}` : `-₹${delta}`})
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── RenewalBreakdownCard – real data from backend ─────────────────────── */
export function RenewalBreakdownCard({ renewalPreview, renewalLoading, onRenew }) {
  // If backend data available, use it
  if (!renewalLoading && renewalPreview?.has_policy && renewalPreview?.breakdown) {
    const bd    = renewalPreview.breakdown;
    const tier  = renewalPreview.current_tier || 'standard';
    const total = renewalPreview.renewal_premium;

    const rows = [
      ['Base Premium',       `₹${bd.base}`,                             `${tier} plan`,          false],
      ['Zone Risk Factor',   `+₹${bd.zone_risk ?? 0}`,                  'Zone surcharge',        false],
      ['Seasonal Index',     `×${Number(bd.seasonal_index ?? 1).toFixed(2)}`,  'City-specific monthly', false],
      ['RIQI Adjustment',   `×${Number(bd.riqi_adjustment ?? 1).toFixed(2)}`, bd.riqi_band || '',    false],
      ['Activity Tier Factor', `×${Number(bd.activity_factor ?? 1).toFixed(2)}`, tier,              false],
      ['Loyalty Discount',   `×${Number(bd.loyalty_discount ?? 1).toFixed(2)}`,
        renewalPreview.loyalty_streak_weeks ? `${renewalPreview.loyalty_streak_weeks}-week streak` : '',
        bd.loyalty_discount < 1],
      ['Platform Fee',       '₹0',                                       'Waived',                false],
    ];

    return (
      <div className="prf-card">
        <div className="prf-card-body">
          <p className="prf-section-title">🔄 Next Week Premium Breakdown</p>
          <p className="prf-section-sub">All formula factors — recalculated every Monday</p>
          {rows.map(([k, v, note, neg]) => (
            <div className="ren-row" key={k}>
              <span className="ren-key">{k}{note ? <span className="ren-note">({note})</span> : null}</span>
              <span className={`ren-val${neg ? ' neg' : ''}`}>{v}</span>
            </div>
          ))}
          <div className="ren-total">
            <span>Total Next Week</span>
            <span className="val">₹{total}</span>
          </div>
          {renewalPreview.expires_at && (
            <p style={{ fontSize: 11, color: 'var(--text-light)', marginTop: 10 }}>
              Current policy expires {new Date(renewalPreview.expires_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
            </p>
          )}
          {renewalPreview.renewal_available && onRenew && (
            <button className="prf-btn-primary" style={{ marginTop: 14 }} onClick={onRenew}>
              Renew Now
            </button>
          )}
        </div>
      </div>
    );
  }

  if (renewalLoading) {
    return (
      <div className="prf-card">
        <div className="prf-card-body">
          <p className="prf-section-title">🔄 Next Week Premium Breakdown</p>
          <p style={{ fontSize: 13, color: 'var(--text-light)' }}>Loading renewal data…</p>
        </div>
      </div>
    );
  }

  if (!renewalPreview?.has_policy) {
    return (
      <div className="prf-card">
        <div className="prf-card-body">
          <p className="prf-section-title">🔄 Next Week Premium Breakdown</p>
          <p style={{ fontSize: 13, color: 'var(--text-light)' }}>
            {renewalPreview?.message || 'No active policy found.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="prf-card">
      <div className="prf-card-body">
        <p className="prf-section-title">🔄 Next Week Premium Breakdown</p>
        <p style={{ fontSize: 13, color: 'var(--text-light)' }}>
          Renewal pricing is unavailable right now. Refresh after backend premium data is ready.
        </p>
      </div>
    </div>
  );
}

/* ─── Main Profile ──────────────────────────────────────────────────────── */
export function Profile() {
  const navigate = useNavigate();
  const { user, logout, refreshUser } = useAuth();

  const [editing,  setEditing]  = useState(false);
  const [name,     setName]     = useState(user?.name || '');
  const [language, setLanguage] = useState(user?.language_pref || 'en');
  const [saving,   setSaving]   = useState(false);
  const [upiId,    setUpiId]    = useState(user?.upi_id || '');
  const [kyc,      setKyc]      = useState(user?.kyc || null);
  const [bankInfo, setBankInfo] = useState({ 
    bank_name: user?.bank_name, 
    account_number: user?.account_number, 
    ifsc_code: user?.ifsc_code 
  });

  const [zoneHistoryData, setZoneHistoryData] = useState(null);
  const [historyLoading,  setHistoryLoading]  = useState(true);
  const [renewalPreview,  setRenewalPreview]  = useState(null);
  const [renewalLoading,  setRenewalLoading]  = useState(true);
  const [legalModal,      setLegalModal]     = useState(null); // 'terms', 'privacy', 'support', 'rapidbot', 'privacy_consent'


  // ── Load zone history ─────────────────────────────────────────────────────
  useEffect(() => {
    api.getZoneHistory()
      .then(data => setZoneHistoryData(data))
      .catch(() => setZoneHistoryData({ history: [], total: 0, has_history: false }))
      .finally(() => setHistoryLoading(false));
  }, []);

  // ── Load renewal preview ──────────────────────────────────────────────────
  useEffect(() => {
    api.getRenewalPreview()
      .then(data => setRenewalPreview(data))
      .catch(() => setRenewalPreview(null))
      .finally(() => setRenewalLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      await api.updateProfile({ name, language_pref: language });
      await refreshUser();
      setEditing(false);
    } catch (e) { alert(e.message); } finally { setSaving(false); }
  }

  return (
    <>
      <style>{S}</style>
      <div className="prf-wrap">

        {/* ── Hero ── */}
        <div className="prf-hero">
          <div className="prf-avatar">P</div>
          <div>
            <p className="prf-hero-name">{user?.name}</p>
            <p className="prf-hero-phone">{user?.phone}</p>
            <p className="prf-hero-plat">{user?.platform} Partner</p>
          </div>
        </div>

        {/* ── Edit Info ── */}
        <div className="prf-card">
          <div className="prf-card-body">
            <p className="prf-section-title">Personal Info</p>
            {editing ? (
              <>
                <div className="prf-field">
                  <label className="prf-label">Full Name</label>
                  <input className="prf-input" value={name} onChange={e => setName(e.target.value)} />
                </div>
                <div className="prf-field">
                  <label className="prf-label">Language</label>
                  <select className="prf-select" value={language} onChange={e => setLanguage(e.target.value)}>
                    {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
                  </select>
                </div>
                <div className="prf-btn-row">
                  <button className="prf-btn-secondary" style={{ flex: 1 }} onClick={() => setEditing(false)}>Cancel</button>
                  <button className="prf-btn-primary" style={{ flex: 2 }} onClick={handleSave} disabled={saving}>
                    {saving ? 'Saving…' : 'Save Changes'}
                  </button>
                </div>
              </>
            ) : (
              <button className="prf-btn-outline" style={{ width: '100%' }} onClick={() => setEditing(true)}>
                Edit Profile
              </button>
            )}
          </div>
        </div>

        {/* ── Zone chip – show real name/code if available ── */}
        {user?.zone_id && (
          <div className="prf-card">
            <div className="prf-card-body">
              <p className="prf-section-title">Your Zone</p>
              <div className="zone-chip">
                {user.zone_name
                  ? `${user.zone_name}${user.zone_code ? ` · ${user.zone_code}` : ''}`
                  : `Zone #${user.zone_id}`}
              </div>
            </div>
          </div>
        )}

        {/* ── Zone History – real backend data ── */}
        <ZoneHistorySection zoneHistoryData={zoneHistoryData} loading={historyLoading} />

        {/* ── Renewal Breakdown – real backend data ── */}
        <RenewalBreakdownCard
          renewalPreview={renewalPreview}
          renewalLoading={renewalLoading}
          onRenew={() => navigate('/policy')}
        />

        {/* ── UPI Linking ── */}
        <div className="prf-card">
          <div className="prf-card-body">
            <p className="prf-section-title">UPI Linking</p>
            <p className="prf-section-sub">Link your UPI ID to receive claim payouts instantly</p>
            <UpiSetup currentUpiId={upiId} onSave={u => setUpiId(u)} />
          </div>
        </div>

        {/* ── Bank Account (IMPS Fallback) ── */}
        <div className="prf-card">
          <div className="prf-card-body">
            <p className="prf-section-title">Bank Account (IMPS Fallback)</p>
            <p className="prf-section-sub">Backup payout channel if UPI fails or is unlinked</p>
            <BankSetup 
              partner={{...user, ...bankInfo}} 
              onSave={b => setBankInfo(b)} 
            />
          </div>
        </div>

        {/* ── KYC ── */}
        <div className="prf-card">
          <div className="prf-card-body">
            <p className="prf-section-title">KYC Verification</p>
            <p className="prf-section-sub">Complete KYC to unlock higher claim limits</p>
            <KycSetup currentKyc={kyc} onSave={k => setKyc(k)} />
          </div>
        </div>

        {/* ── Notifications ── */}
        <div className="prf-card">
          <div className="prf-card-body">
            <p className="prf-section-title">Notifications</p>
            <NotificationToggle />
          </div>
        </div>

        {/* ── Account links ── */}
        <div className="prf-card">
          <div className="prf-card-body" style={{ padding: '10px 18px' }}>
            <button className="prf-action-row" onClick={() => setLegalModal('terms')}>
              <span>Terms of Service</span>
              <span style={{ color: 'var(--text-light)' }}>-&gt;</span>
            </button>
            <button className="prf-action-row" onClick={() => setLegalModal('privacy')}>
              <span>Privacy Policy</span>
              <span style={{ color: 'var(--text-light)' }}>-&gt;</span>
            </button>
            <button className="prf-action-row" onClick={() => setLegalModal('privacy_consent')}>
              <span>Your Data & Consent</span>
              <span style={{ color: 'var(--text-light)' }}>-&gt;</span>
            </button>
            <button className="prf-action-row" onClick={() => setLegalModal('support')}>
              <span>Help & Support</span>
              <span style={{ color: 'var(--text-light)' }}>-&gt;</span>
            </button>
          </div>
        </div>

        {/* ── Legal Modals ── */}
        {legalModal && (
          <div className="legal-overlay" onClick={() => setLegalModal(null)}>
            <div 
              className="legal-sheet" 
              onClick={e => e.stopPropagation()}
              style={legalModal === 'rapidbot' ? { padding: 0, overflow: 'hidden' } : {}}
            >
              {/* Header logic (hidden for RapidBot to use its own) */}
              {legalModal !== 'rapidbot' && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <h2 className="legal-title">
                    {legalModal === 'terms' && 'Terms of Service'}
                    {legalModal === 'privacy' && 'Privacy Policy'}
                    {legalModal === 'privacy_consent' && 'Your Data & Consent'}
                    {legalModal === 'support' && 'Help & Support'}
                  </h2>
                  <button 
                    onClick={() => setLegalModal(null)}
                    style={{ background: 'var(--gray-bg)', border: 'none', borderRadius: '50%', width: 32, height: 32, cursor: 'pointer', fontSize: 18 }}
                  >✕</button>
                </div>
              )}

              <div className={legalModal === 'rapidbot' ? '' : 'legal-body'} style={legalModal === 'rapidbot' ? { height: '85vh' } : {}}>
                {legalModal === 'rapidbot' && <RapidBot />}
                {legalModal === 'privacy_consent' && <PrivacyConsentPanel />}
                
                {legalModal === 'terms' && (
                  <>
                    <div className="legal-section">
                      <h3 className="legal-h3">1. Coverage Scope</h3>
                      <p>RapidCover provides parametric insurance for gig delivery partners. Payouts are triggered automatically based on hyper-local weather and civic data.</p>
                    </div>
                    <div className="legal-section">
                      <h3 className="legal-h3">2. Payout Eligibility</h3>
                      <p>Partners must maintain an active delivery status during the disruption window. Claims are processed via real-time data oracles and are final once issued.</p>
                    </div>
                    <div className="legal-section">
                      <h3 className="legal-h3">3. Fair Use</h3>
                      <p>Any attempt to manipulate GPS data or simulate false platform activity will result in immediate policy cancellation without refund.</p>
                    </div>
                  </>
                )}

                {legalModal === 'privacy' && (
                  <>
                    <div className="legal-section">
                      <h3 className="legal-h3">1. Data Encryption</h3>
                      <p>Your Aadhaar and PAN details are hashed using SHA-256 before storage. We do not store plain-text identity documents.</p>
                    </div>
                    <div className="legal-section">
                      <h3 className="legal-h3">2. Location Privacy</h3>
                      <p>Location data is used exclusively for verifying your presence in your assigned zone during disruption events. We do not track you outside of active coverage windows.</p>
                    </div>
                    <div className="legal-section">
                      <h3 className="legal-h3">3. Payment Security</h3>
                      <p>UPI IDs are stored only to facilitate instant payouts via NPCI-approved gateways. We do not have access to your bank account details.</p>
                    </div>
                  </>
                )}

                {legalModal === 'support' && (
                  <>
                    <p style={{ marginBottom: 15 }}>Need help? Our AI assistant or support team is here for you.</p>
                    <div className="grok-card" onClick={() => setLegalModal('rapidbot')}>
                      <div className="bmsg-bot-avatar" style={{ border: '1.5px solid rgba(61, 184, 92, 0.3)', background: '#ffffff', color: '#3DB85C' }}>R</div>
                      <div>
                        <div style={{ fontSize: 15 }}>Talk to RapidBot AI</div>
                        <div style={{ fontSize: 11, opacity: 0.7, fontWeight: 400 }}>Instant help with policy locks, payouts & zones</div>
                      </div>
                    </div>
                    <div style={{ height: 16 }} />
                    <a href="https://wa.me/919999999999" className="support-card" target="_blank" rel="noreferrer">
                      <div>
                        <div style={{ fontSize: 14 }}>WhatsApp Support</div>
                        <div style={{ fontSize: 12, opacity: 0.8, fontWeight: 400 }}>Instant reply within 5 mins</div>
                      </div>
                    </a>
                    <div style={{ height: 12 }} />
                    <a href="mailto:support@rapidcover.in" className="support-card" style={{ background: '#f1f5f9', color: '#475569', borderColor: '#cbd5e1' }}>
                      <div>
                        <div style={{ fontSize: 14 }}>Email Ticketing</div>
                        <div style={{ fontSize: 12, opacity: 0.8, fontWeight: 400 }}>support@rapidcover.in</div>
                      </div>
                    </a>
                  </>
                )}
              </div>
              
              <button 
                className="prf-btn-primary" 
                style={{ marginTop: 20 }}
                onClick={() => setLegalModal(null)}
              >
                Understood
              </button>
            </div>
          </div>
        )}

        {/* ── Logout ── */}
        <button className="prf-btn-danger" onClick={() => { logout(); navigate('/login'); }}>Logout</button>

        <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-light)' }}>RapidCover v1.0.0</p>
      </div>
    </>
  );
}

export default Profile;
