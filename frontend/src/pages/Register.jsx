import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { TermsModal } from '../components/ui/TermsModal';

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=DM+Sans:wght@400;500;600&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

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
    --warning:       #d97706;
  }

  .reg-screen {
    width: 100%;
    min-height: 100vh;
    background: var(--white);
    display: flex;
    flex-direction: column;
    align-items: center;
    font-family: 'DM Sans', sans-serif;
    padding: 32px 28px 48px;
  }

  .reg-logo {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 28px;
  }

  .reg-logo-icon {
    width: 56px;
    height: 56px;
    background: var(--green-primary);
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 6px 18px rgba(61,184,92,0.35);
    margin-bottom: 12px;
  }

  .reg-logo-brand {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 22px;
    color: var(--text-dark);
  }

  .reg-logo-sub {
    font-size: 11px;
    color: var(--text-light);
    font-weight: 500;
    letter-spacing: 0.4px;
    margin-top: 3px;
  }

  .reg-card {
    width: 100%;
    max-width: 360px;
    background: var(--white);
    border-radius: 24px;
    padding: 28px 24px;
    box-shadow: 0 4px 32px rgba(0,0,0,0.08);
  }

  .reg-steps {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin-bottom: 24px;
  }

  .reg-step-dot {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Nunito', sans-serif;
    font-size: 12px;
    font-weight: 800;
    border: 2px solid var(--border);
    background: var(--gray-bg);
    color: var(--text-light);
    flex-shrink: 0;
    transition: all 0.25s ease;
  }

  .reg-step-dot.active {
    background: var(--green-primary);
    border-color: var(--green-primary);
    color: var(--white);
    box-shadow: 0 3px 10px rgba(61,184,92,0.4);
  }

  .reg-step-dot.done {
    background: var(--green-light);
    border-color: var(--green-primary);
    color: var(--green-dark);
  }

  .reg-step-line {
    flex: 1;
    height: 2px;
    background: var(--border);
    margin: 0 4px;
    transition: background 0.25s ease;
  }

  .reg-step-line.done { background: var(--green-primary); }

  .reg-step-label {
    font-size: 10px;
    color: var(--text-light);
    text-align: center;
    margin-bottom: 18px;
    font-family: 'Nunito', sans-serif;
    font-weight: 700;
    letter-spacing: 0.3px;
    text-transform: uppercase;
  }

  .reg-step-label span { color: var(--green-primary); }

  .reg-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 24px;
    color: var(--text-dark);
    margin-bottom: 6px;
  }

  .reg-subtitle {
    font-size: 13px;
    color: var(--text-mid);
    margin-bottom: 24px;
  }

  .reg-field { margin-bottom: 16px; }

  .reg-label {
    font-size: 12.5px;
    font-weight: 600;
    color: var(--text-dark);
    margin-bottom: 6px;
    display: block;
    font-family: 'Nunito', sans-serif;
  }

  .reg-label-hint {
    font-size: 11px;
    color: var(--text-light);
    font-weight: 400;
    margin-left: 6px;
  }

  .reg-input-wrap { position: relative; }

  .reg-input {
    width: 100%;
    padding: 14px 16px;
    border: 1.5px solid var(--border);
    border-radius: 14px;
    font-size: 14px;
    font-family: 'DM Sans', sans-serif;
    color: var(--text-dark);
    background: var(--gray-bg);
    outline: none;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    appearance: none;
    -webkit-appearance: none;
  }

  .reg-input::placeholder { color: #b8c8b8; }

  .reg-input:focus {
    border-color: var(--green-primary);
    box-shadow: 0 0 0 3px rgba(61,184,92,0.12);
    background: var(--white);
  }

  .reg-input.valid   { border-color: var(--green-primary); }
  .reg-input.invalid { border-color: var(--warning); }

  .reg-input-icon {
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 14px;
    pointer-events: none;
  }

  .reg-select-wrap { position: relative; }

  .reg-select-wrap::after {
    content: '▾';
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-light);
    pointer-events: none;
    font-size: 13px;
  }

  .reg-gps-btn {
    width: 100%;
    padding: 13px 16px;
    background: var(--green-light);
    border: 1.5px solid #b6dfc0;
    border-radius: 14px;
    color: var(--green-dark);
    font-family: 'Nunito', sans-serif;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-bottom: 10px;
    transition: background 0.2s ease, border-color 0.2s ease;
  }

  .reg-gps-btn:hover:not(:disabled) { background: #d4f0dc; border-color: var(--green-primary); }
  .reg-gps-btn:disabled { opacity: 0.55; cursor: not-allowed; }

  .reg-status {
    font-size: 12.5px;
    margin-bottom: 10px;
    padding: 8px 12px;
    border-radius: 10px;
    line-height: 1.4;
  }

  .reg-status.success { background: var(--green-light); color: var(--green-dark); }
  .reg-status.warning { background: #fef3c7; color: var(--warning); }
  .reg-status.error   { background: #fef2f2; color: var(--error); }

  .reg-hint { font-size: 11.5px; color: var(--text-light); margin-top: 5px; }
  .reg-hint.valid   { color: var(--green-dark); }
  .reg-hint.invalid { color: var(--warning); }

  .reg-btn {
    width: 100%;
    padding: 16px;
    background: var(--green-primary);
    border: none;
    border-radius: 16px;
    color: var(--white);
    font-family: 'Nunito', sans-serif;
    font-size: 16px;
    font-weight: 800;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s;
    box-shadow: 0 8px 22px rgba(61,184,92,0.38);
    margin-top: 8px;
  }

  .reg-btn::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.18) 0%, transparent 55%);
    pointer-events: none;
    border-radius: inherit;
  }

  .reg-btn:active { transform: scale(0.97); }
  .reg-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

  .reg-btn-row { display: flex; gap: 10px; margin-top: 8px; }

  .reg-btn-back {
    flex: 1;
    padding: 16px;
    background: var(--gray-bg);
    border: 1.5px solid var(--border);
    border-radius: 16px;
    color: var(--text-mid);
    font-family: 'Nunito', sans-serif;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .reg-btn-back:hover { background: var(--border); }

  .reg-btn-next {
    flex: 2;
    padding: 16px;
    background: var(--green-primary);
    border: none;
    border-radius: 16px;
    color: var(--white);
    font-family: 'Nunito', sans-serif;
    font-size: 15px;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 6px 18px rgba(61,184,92,0.35);
    transition: transform 0.15s ease, opacity 0.15s;
  }

  .reg-btn-next:active { transform: scale(0.97); }
  .reg-btn-next:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

  .reg-btn .spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255,255,255,0.4);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    vertical-align: middle;
    margin-right: 8px;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .reg-error {
    font-size: 12.5px;
    color: var(--error);
    background: #fef2f2;
    border-radius: 10px;
    padding: 8px 12px;
    margin-bottom: 12px;
    text-align: center;
  }

  .reg-footer {
    margin-top: 24px;
    font-size: 13px;
    color: var(--text-mid);
    text-align: center;
  }

  .reg-footer a {
    color: var(--green-primary);
    font-weight: 700;
    text-decoration: none;
    font-family: 'Nunito', sans-serif;
  }

  .reg-kyc-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #fff8e1;
    border: 1.5px solid #f6cc3c;
    border-radius: 10px;
    padding: 7px 12px;
    font-size: 12px;
    color: #92610a;
    font-family: 'Nunito', sans-serif;
    font-weight: 700;
    margin-bottom: 18px;
  }

  .reg-file-label {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 13px 16px;
    border: 1.5px dashed var(--border);
    border-radius: 14px;
    background: var(--gray-bg);
    cursor: pointer;
    font-size: 13px;
    color: var(--text-mid);
    transition: border-color 0.2s, background 0.2s;
  }

  .reg-file-label:hover, .reg-file-label.has-file {
    border-color: var(--green-primary);
    background: var(--green-light);
    color: var(--green-dark);
  }

  .reg-file-input { display: none; }

  .reg-upi-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--green-light);
    border: 1.5px solid #b6dfc0;
    border-radius: 10px;
    padding: 7px 12px;
    font-size: 12px;
    color: var(--green-dark);
    font-family: 'Nunito', sans-serif;
    font-weight: 700;
    margin-bottom: 18px;
  }

  .reg-review-section {
    background: var(--gray-bg);
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 14px;
  }

  .reg-review-section-title {
    font-family: 'Nunito', sans-serif;
    font-size: 11px;
    font-weight: 800;
    color: var(--text-light);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 10px;
  }

  .reg-review-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
  }

  .reg-review-row:last-child { border-bottom: none; }

  .reg-review-key { color: var(--text-light); font-size: 12px; }

  .reg-review-val {
    color: var(--text-dark);
    font-weight: 600;
    font-family: 'Nunito', sans-serif;
    text-align: right;
    max-width: 60%;
    word-break: break-all;
  }

  .reg-review-val.missing { color: var(--text-light); font-weight: 400; font-style: italic; }

  .reg-review-val.badge {
    background: var(--green-light);
    color: var(--green-dark);
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 11px;
  }

  /* Terms prompt on review step */
  .reg-terms-prompt {
    background: #fff8e1;
    border: 1.5px solid #f6d860;
    border-radius: 14px;
    padding: 13px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    font-size: 12.5px;
    color: #7a5800;
    font-family: 'DM Sans', sans-serif;
    line-height: 1.4;
  }
`;

const PLATFORMS = [
  { value: 'zepto', label: 'Zepto' },
  { value: 'blinkit', label: 'Blinkit' },
];

const STEPS = [
  { id: 'basic', label: 'Basic Info' },
  { id: 'kyc', label: 'KYC' },
  { id: 'upi', label: 'UPI' },
  { id: 'review', label: 'Review' },
];

function validateUPI(upi) { return /^[\w.\-]{3,}@[\w]{3,}$/.test(upi.trim()); }
function validateAadhaar(val) { return /^\d{12}$/.test(val.replace(/\s/g, '')); }
function validatePAN(val) { return /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(val.trim().toUpperCase()); }

export function Register() {
  const navigate = useNavigate();

  const [step, setStep] = useState(0);
  const [showTerms, setShowTerms] = useState(false);

  const [formData, setFormData] = useState({
    phone: '', name: '', platform: 'zepto', partner_id: '', zone_id: '',
    aadhaarNumber: '', panNumber: '', aadhaarFile: null,
    upiId: '',
  });

  const [zones, setZones] = useState([]);
  const [zonesLoading, setZonesLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [gpsStatus, setGpsStatus] = useState('idle');
  const [detectedZone, setDetectedZone] = useState(null);
  const [partnerIdStatus, setPartnerIdStatus] = useState('idle');
  const [partnerIdMessage, setPartnerIdMessage] = useState('');

  useEffect(() => {
    async function loadZones() {
      try { const z = await api.getZones(); setZones(z); }
      catch (err) { console.error('Failed to load zones:', err); }
      finally { setZonesLoading(false); }
    }
    loadZones();
  }, []);

  const MAX_DETECTION_DISTANCE_KM = 25;

  async function detectLocation() {
    if (!navigator.geolocation) { setGpsStatus('error'); return; }
    setGpsStatus('loading');
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const result = await api.getNearestZones(latitude, longitude);
          if (result.length > 0) {
            const nearest = result[0];
            if (nearest.distance_km <= MAX_DETECTION_DISTANCE_KM) {
              setDetectedZone(nearest);
              setFormData(prev => ({ ...prev, zone_id: String(nearest.zone.id) }));
              setGpsStatus('success');
            } else {
              setDetectedZone(nearest);
              setGpsStatus('too_far');
            }
          } else { setGpsStatus('error'); }
        } catch { setGpsStatus('error'); }
      },
      (err) => { setGpsStatus(err.code === 1 ? 'denied' : 'error'); },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function handleChange(e) {
    const { name, value, files } = e.target;
    if (name === 'aadhaarFile') {
      setFormData(prev => ({ ...prev, aadhaarFile: files[0] || null }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
    if (name === 'platform') { setPartnerIdStatus('idle'); setPartnerIdMessage(''); }
  }

  async function validatePartnerId() {
    const pid = formData.partner_id.trim();
    if (!pid) { setPartnerIdStatus('idle'); setPartnerIdMessage(''); return; }
    setPartnerIdStatus('checking');
    try {
      const result = await api.validatePartnerId(pid, formData.platform);
      setPartnerIdStatus(result.valid ? 'valid' : 'invalid');
      setPartnerIdMessage(result.message);
    } catch {
      setPartnerIdStatus('invalid');
      setPartnerIdMessage('Unable to verify partner ID');
    }
  }

  function canProceedFromBasic() { return formData.name.trim() && formData.phone.trim(); }
  function canProceedFromKyc() {
    if (formData.aadhaarNumber.trim() && !validateAadhaar(formData.aadhaarNumber)) return false;
    if (formData.panNumber.trim() && !validatePAN(formData.panNumber)) return false;
    return true;
  }
  function canProceedFromUpi() {
    if (!formData.upiId.trim()) return true;
    return validateUPI(formData.upiId);
  }

  function goNext() { setError(''); setStep(s => s + 1); }
  function goBack() { setError(''); setStep(s => s - 1); }

  // Called when user clicks "Create Account" on review — show terms first
  function handleReviewSubmit() { setShowTerms(true); }

  // Called when user accepts terms in the modal — now actually submit
  async function handleFinalSubmit() {
    setShowTerms(false);
    setError('');
    setLoading(true);
    try {
      const cleanData = {
        phone: formData.phone.replace(/\s/g, ''),
        name: formData.name.trim(),
        platform: formData.platform,
        partner_id: formData.partner_id.trim() || null,
        zone_id: formData.zone_id ? parseInt(formData.zone_id, 10) : null,
        kyc: {
          aadhaar_number: formData.aadhaarNumber.replace(/\s/g, '') || null,
          pan_number: formData.panNumber.trim().toUpperCase() || null,
          kyc_status: formData.aadhaarNumber ? 'pending' : 'skipped',
        },
        upi_id: formData.upiId.trim() || null,
      };
      await api.register(cleanData);
      navigate('/login');
      alert('Registration successful! Please login.');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleDeclineTerms() { setShowTerms(false); }

  // Derived
  const pidInputClass = `reg-input${partnerIdStatus === 'valid' ? ' valid' : partnerIdStatus === 'invalid' ? ' invalid' : ''}`;
  const pidIcon = partnerIdStatus === 'checking' ? '⏳' : partnerIdStatus === 'valid' ? '✓' : partnerIdStatus === 'invalid' ? '✗' : null;
  const upiValid = formData.upiId.trim() ? validateUPI(formData.upiId) : null;
  const aadhaarValid = formData.aadhaarNumber.trim() ? validateAadhaar(formData.aadhaarNumber) : null;
  const panValid = formData.panNumber.trim() ? validatePAN(formData.panNumber) : null;
  const selectedZone = zones.find(z => String(z.id) === String(formData.zone_id));

  function StepProgress() {
    return (
      <>
        <div className="reg-steps">
          {STEPS.map((s, i) => (
            <React.Fragment key={s.id}>
              <div className={`reg-step-dot${i === step ? ' active' : i < step ? ' done' : ''}`}>
                {i < step ? '✓' : i + 1}
              </div>
              {i < STEPS.length - 1 && (
                <div className={`reg-step-line${i < step ? ' done' : ''}`} />
              )}
            </React.Fragment>
          ))}
        </div>
        <div className="reg-step-label">
          Step {step + 1} of {STEPS.length} — <span>{STEPS[step].label}</span>
        </div>
      </>
    );
  }

  function StepBasic() {
    return (
      <>
        <div className="reg-title">Create Account</div>
        <div className="reg-subtitle">Get income protection in minutes.</div>

        <div className="reg-field">
          <label className="reg-label">Full Name</label>
          <input className="reg-input" name="name" placeholder="Enter your name" value={formData.name} onChange={handleChange} />
        </div>

        <div className="reg-field">
          <label className="reg-label">Phone Number</label>
          <input className="reg-input" name="phone" type="tel" placeholder="+91 9876543210" value={formData.phone} onChange={handleChange} />
        </div>

        <div className="reg-field">
          <label className="reg-label">Platform</label>
          <div className="reg-select-wrap">
            <select className="reg-input" name="platform" value={formData.platform} onChange={handleChange}>
              {PLATFORMS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </div>
        </div>

        <div className="reg-field">
          <label className="reg-label">Partner ID <span className="reg-label-hint">(optional)</span></label>
          <div className="reg-input-wrap">
            <input className={pidInputClass} type="text" name="partner_id"
              placeholder={formData.platform === 'zepto' ? 'ZPT123456' : 'BLK123456'}
              value={formData.partner_id} onChange={handleChange} onBlur={validatePartnerId}
              style={{ paddingRight: pidIcon ? '40px' : '16px' }} />
            {pidIcon && (
              <span className="reg-input-icon" style={{ color: partnerIdStatus === 'valid' ? 'var(--green-primary)' : 'var(--warning)' }}>
                {pidIcon}
              </span>
            )}
          </div>
          <div className={`reg-hint${partnerIdMessage ? ` ${partnerIdStatus}` : ''}`}>
            {partnerIdMessage || `Your ${formData.platform === 'zepto' ? 'Zepto' : 'Blinkit'} partner ID`}
          </div>
        </div>

        <div className="reg-field">
          <label className="reg-label">Dark Store Zone</label>
          <button type="button" className="reg-gps-btn" onClick={detectLocation} disabled={gpsStatus === 'loading' || zonesLoading}>
            {gpsStatus === 'loading' ? <><span>⏳</span> Detecting location...</> : <><span>📍</span> Detect My Zone</>}
          </button>
          {gpsStatus === 'success' && detectedZone && <div className="reg-status success">✓ Detected: {detectedZone.zone.name} ({detectedZone.distance_km} km away)</div>}
          {gpsStatus === 'too_far' && detectedZone && <div className="reg-status warning">No zones near you. Nearest: {detectedZone.zone.name} ({detectedZone.distance_km} km). Select manually.</div>}
          {gpsStatus === 'denied' && <div className="reg-status warning">Location access denied. Select zone manually.</div>}
          {gpsStatus === 'error' && <div className="reg-status error">Could not detect location. Select zone manually.</div>}
          <div className="reg-select-wrap">
            <select className="reg-input" name="zone_id" value={formData.zone_id} onChange={handleChange} disabled={zonesLoading}>
              {zonesLoading ? <option value="">Loading zones...</option>
                : zones.length === 0 ? <option value="">No zones available — contact admin</option>
                  : <><option value="">Select your zone</option>{zones.map(z => <option key={z.id} value={z.id}>{z.city} - {z.name} ({z.code})</option>)}</>}
            </select>
          </div>
          <div className="reg-hint">
            {gpsStatus === 'success' ? 'Zone auto-detected. You can change it if needed.'
              : gpsStatus === 'too_far' ? 'Select from available zones below'
                : 'Use GPS detection or choose manually'}
          </div>
        </div>

        {error && <div className="reg-error">{error}</div>}
        <button className="reg-btn" onClick={goNext} disabled={!canProceedFromBasic()}>Continue →</button>
      </>
    );
  }

  function StepKyc() {
    return (
      <>
        <div className="reg-title">KYC Verification</div>
        <div className="reg-subtitle">Quick identity check — you can skip for now.</div>
        <div className="reg-kyc-badge">🔒 Mock KYC — No real data is stored</div>

        <div className="reg-field">
          <label className="reg-label">Aadhaar Number <span className="reg-label-hint">(optional)</span></label>
          <div className="reg-input-wrap">
            <input className={`reg-input${aadhaarValid === true ? ' valid' : aadhaarValid === false ? ' invalid' : ''}`}
              name="aadhaarNumber" placeholder="1234 5678 9012" maxLength={14}
              value={formData.aadhaarNumber} onChange={handleChange} />
            {aadhaarValid !== null && <span className="reg-input-icon" style={{ color: aadhaarValid ? 'var(--green-primary)' : 'var(--warning)' }}>{aadhaarValid ? '✓' : '✗'}</span>}
          </div>
          <div className={`reg-hint${aadhaarValid === false ? ' invalid' : aadhaarValid === true ? ' valid' : ''}`}>
            {aadhaarValid === false ? 'Must be 12 digits' : aadhaarValid === true ? 'Looks good!' : '12-digit Aadhaar number'}
          </div>
        </div>

        <div className="reg-field">
          <label className="reg-label">PAN Number <span className="reg-label-hint">(optional)</span></label>
          <div className="reg-input-wrap">
            <input className={`reg-input${panValid === true ? ' valid' : panValid === false ? ' invalid' : ''}`}
              name="panNumber" placeholder="ABCDE1234F" maxLength={10}
              value={formData.panNumber}
              onChange={e => handleChange({ target: { name: 'panNumber', value: e.target.value.toUpperCase() } })} />
            {panValid !== null && <span className="reg-input-icon" style={{ color: panValid ? 'var(--green-primary)' : 'var(--warning)' }}>{panValid ? '✓' : '✗'}</span>}
          </div>
          <div className={`reg-hint${panValid === false ? ' invalid' : panValid === true ? ' valid' : ''}`}>
            {panValid === false ? 'Format: ABCDE1234F' : panValid === true ? 'Valid PAN format' : 'e.g. ABCDE1234F'}
          </div>
        </div>

        <div className="reg-field">
          <label className="reg-label">Upload Aadhaar <span className="reg-label-hint">(optional)</span></label>
          <label className={`reg-file-label${formData.aadhaarFile ? ' has-file' : ''}`} htmlFor="aadhaarFileInput">
            <span>{formData.aadhaarFile ? '✅' : '📎'}</span>
            <span>{formData.aadhaarFile ? formData.aadhaarFile.name : 'Tap to upload Aadhaar (image/PDF)'}</span>
          </label>
          <input id="aadhaarFileInput" className="reg-file-input" type="file" name="aadhaarFile" accept="image/*,.pdf" onChange={handleChange} />
          <div className="reg-hint">JPEG, PNG or PDF · Max 5MB · Mock upload</div>
        </div>

        {error && <div className="reg-error">{error}</div>}
        <div className="reg-btn-row">
          <button className="reg-btn-back" onClick={goBack}>← Back</button>
          <button className="reg-btn-next" onClick={goNext} disabled={!canProceedFromKyc()}>Continue →</button>
        </div>
      </>
    );
  }

  function StepUpi() {
    return (
      <>
        <div className="reg-title">Link UPI ID</div>
        <div className="reg-subtitle">For faster claim payouts — optional.</div>
        <div className="reg-upi-badge">💳 UPI payouts come directly to your account</div>

        <div className="reg-field">
          <label className="reg-label">UPI ID <span className="reg-label-hint">(optional)</span></label>
          <div className="reg-input-wrap">
            <input className={`reg-input${upiValid === true ? ' valid' : upiValid === false ? ' invalid' : ''}`}
              name="upiId" placeholder="yourname@upi" value={formData.upiId} onChange={handleChange} />
            {upiValid !== null && <span className="reg-input-icon" style={{ color: upiValid ? 'var(--green-primary)' : 'var(--warning)' }}>{upiValid ? '✓' : '✗'}</span>}
          </div>
          <div className={`reg-hint${upiValid === false ? ' invalid' : upiValid === true ? ' valid' : ''}`}>
            {upiValid === false ? 'Invalid format — try yourname@okhdfcbank' : upiValid === true ? 'Valid UPI ID ✓' : 'e.g. name@okaxis, phone@ybl'}
          </div>
        </div>

        <div className="reg-status" style={{ background: 'var(--gray-bg)', color: 'var(--text-mid)', marginTop: 4 }}>
          ℹ️ You can also add or update your UPI ID later from your Profile.
        </div>

        {error && <div className="reg-error">{error}</div>}
        <div className="reg-btn-row">
          <button className="reg-btn-back" onClick={goBack}>← Back</button>
          <button className="reg-btn-next" onClick={goNext} disabled={!canProceedFromUpi()}>Review →</button>
        </div>
      </>
    );
  }

  function StepReview() {
    return (
      <>
        <div className="reg-title">Review & Confirm</div>
        <div className="reg-subtitle">Double-check before creating your account.</div>

        <div className="reg-review-section">
          <div className="reg-review-section-title">Basic Info</div>
          <div className="reg-review-row"><span className="reg-review-key">Name</span><span className="reg-review-val">{formData.name || '—'}</span></div>
          <div className="reg-review-row"><span className="reg-review-key">Phone</span><span className="reg-review-val">{formData.phone || '—'}</span></div>
          <div className="reg-review-row"><span className="reg-review-key">Platform</span><span className="reg-review-val badge">{PLATFORMS.find(p => p.value === formData.platform)?.label}</span></div>
          <div className="reg-review-row"><span className="reg-review-key">Partner ID</span><span className={`reg-review-val${!formData.partner_id ? ' missing' : ''}`}>{formData.partner_id || 'Not provided'}</span></div>
          <div className="reg-review-row"><span className="reg-review-key">Zone</span><span className={`reg-review-val${!selectedZone ? ' missing' : ''}`}>{selectedZone ? `${selectedZone.city} - ${selectedZone.name}` : 'Not selected'}</span></div>
        </div>

        <div className="reg-review-section">
          <div className="reg-review-section-title">KYC</div>
          <div className="reg-review-row"><span className="reg-review-key">Aadhaar</span><span className={`reg-review-val${!formData.aadhaarNumber ? ' missing' : ''}`}>{formData.aadhaarNumber ? `••••  ••••  ${formData.aadhaarNumber.replace(/\s/g, '').slice(-4)}` : 'Skipped'}</span></div>
          <div className="reg-review-row"><span className="reg-review-key">PAN</span><span className={`reg-review-val${!formData.panNumber ? ' missing' : ''}`}>{formData.panNumber || 'Skipped'}</span></div>
          <div className="reg-review-row"><span className="reg-review-key">Aadhaar Doc</span><span className={`reg-review-val${!formData.aadhaarFile ? ' missing' : ''}`}>{formData.aadhaarFile ? `✅ ${formData.aadhaarFile.name}` : 'Not uploaded'}</span></div>
        </div>

        <div className="reg-review-section">
          <div className="reg-review-section-title">UPI</div>
          <div className="reg-review-row"><span className="reg-review-key">UPI ID</span><span className={`reg-review-val${!formData.upiId ? ' missing' : ''}`}>{formData.upiId || 'Not linked'}</span></div>
        </div>

        {/* Terms prompt */}
        <div className="reg-terms-prompt">
          <span style={{ fontSize: 20 }}>📋</span>
          <span>Next step: Read and accept RapidCover's Terms & Coverage before your policy activates.</span>
        </div>

        {error && <div className="reg-error">{error}</div>}

        <div className="reg-btn-row">
          <button className="reg-btn-back" onClick={goBack}>← Back</button>
          <button className="reg-btn-next" onClick={handleReviewSubmit} disabled={loading}>
            {loading
              ? <span style={{ display: 'inline-block', width: 14, height: 14, border: '2px solid rgba(255,255,255,0.4)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.7s linear infinite', marginRight: 6 }} />
              : null}
            View Terms →
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <style>{styles}</style>

      {/* Terms Modal — shown after review, before final API call */}
      {showTerms && (
        <TermsModal
          onAccept={handleFinalSubmit}
          onDecline={handleDeclineTerms}
        />
      )}

      <div className="reg-screen">
        <div className="reg-logo">
          <div className="reg-logo-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M3 12h3l3-9 4 18 3-9h5" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="reg-logo-brand">RapidCover</div>
          <div className="reg-logo-sub">Parametric Income Intelligence</div>
        </div>

        <div className="reg-card">
          {StepProgress()}
          {step === 0 && StepBasic()}
          {step === 1 && StepKyc()}
          {step === 2 && StepUpi()}
          {step === 3 && StepReview()}
        </div>

        <div className="reg-footer">
          Already registered? <Link to="/login">Login here</Link>
        </div>
      </div>
    </>
  );
}