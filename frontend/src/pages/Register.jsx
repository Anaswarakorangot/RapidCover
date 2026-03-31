import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';

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

  .reg-gps-btn:hover:not(:disabled) {
    background: #d4f0dc;
    border-color: var(--green-primary);
  }

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
`;

const PLATFORMS = [
  { value: 'zepto', label: 'Zepto' },
  { value: 'blinkit', label: 'Blinkit' },
];

export function Register() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    phone: '', name: '', platform: 'zepto', partner_id: '', zone_id: '',
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
      try {
        const zoneData = await api.getZones();
        setZones(zoneData);
      } catch (err) {
        console.error('Failed to load zones:', err);
      } finally {
        setZonesLoading(false);
      }
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
              setFormData((prev) => ({ ...prev, zone_id: String(nearest.zone.id) }));
              setGpsStatus('success');
            } else {
              setDetectedZone(nearest);
              setGpsStatus('too_far');
            }
          } else {
            setGpsStatus('error');
          }
        } catch (err) {
          console.error('Failed to get nearest zones:', err);
          setGpsStatus('error');
        }
      },
      (err) => { setGpsStatus(err.code === 1 ? 'denied' : 'error'); },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
    if (name === 'platform') { setPartnerIdStatus('idle'); setPartnerIdMessage(''); }
  }

  async function validatePartnerId() {
    const partnerId = formData.partner_id.trim();
    if (!partnerId) { setPartnerIdStatus('idle'); setPartnerIdMessage(''); return; }
    setPartnerIdStatus('checking');
    setPartnerIdMessage('');
    try {
      const result = await api.validatePartnerId(partnerId, formData.platform);
      setPartnerIdStatus(result.valid ? 'valid' : 'invalid');
      setPartnerIdMessage(result.message);
    } catch (err) {
      setPartnerIdStatus('invalid');
      setPartnerIdMessage('Unable to verify partner ID');
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const cleanData = {
        ...formData,
        phone: formData.phone.replace(/\s/g, ''),
        partner_id: formData.partner_id.trim() || null,
        zone_id: formData.zone_id ? parseInt(formData.zone_id, 10) : null,
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

  const pidInputClass = `reg-input${partnerIdStatus === 'valid' ? ' valid' : partnerIdStatus === 'invalid' ? ' invalid' : ''}`;
  const pidIcon = partnerIdStatus === 'checking' ? '⏳' : partnerIdStatus === 'valid' ? '✓' : partnerIdStatus === 'invalid' ? '✗' : null;

  return (
    <>
      <style>{styles}</style>
      <div className="reg-screen">

        {/* Logo */}
        <div className="reg-logo">
          <div className="reg-logo-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M3 12h3l3-9 4 18 3-9h5" stroke="white" strokeWidth="2.2"
                strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="reg-logo-brand">RapidCover</div>
          <div className="reg-logo-sub">Parametric Income Intelligence</div>
        </div>

        {/* Card */}
        <div className="reg-card">
          <div className="reg-title">Create Account</div>
          <div className="reg-subtitle">Get income protection in minutes.</div>

          <form onSubmit={handleSubmit}>

            {/* Full Name */}
            <div className="reg-field">
              <label className="reg-label">Full Name</label>
              <input className="reg-input" name="name" placeholder="Enter your name"
                value={formData.name} onChange={handleChange} required />
            </div>

            {/* Phone */}
            <div className="reg-field">
              <label className="reg-label">Phone Number</label>
              <input className="reg-input" name="phone" type="tel" placeholder="+91 9876543210"
                value={formData.phone} onChange={handleChange} required />
            </div>

            {/* Platform */}
            <div className="reg-field">
              <label className="reg-label">Platform</label>
              <div className="reg-select-wrap">
                <select className="reg-input" name="platform" value={formData.platform} onChange={handleChange}>
                  {PLATFORMS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
                </select>
              </div>
            </div>

            {/* Partner ID */}
            <div className="reg-field">
              <label className="reg-label">
                Partner ID <span className="reg-label-hint">(optional)</span>
              </label>
              <div className="reg-input-wrap">
                <input
                  className={pidInputClass}
                  type="text" name="partner_id"
                  placeholder={formData.platform === 'zepto' ? 'ZPT123456' : 'BLK123456'}
                  value={formData.partner_id}
                  onChange={handleChange}
                  onBlur={validatePartnerId}
                  style={{ paddingRight: pidIcon ? '40px' : '16px' }}
                />
                {pidIcon && (
                  <span className="reg-input-icon"
                    style={{ color: partnerIdStatus === 'valid' ? 'var(--green-primary)' : 'var(--warning)' }}>
                    {pidIcon}
                  </span>
                )}
              </div>
              <div className={`reg-hint${partnerIdMessage ? ` ${partnerIdStatus}` : ''}`}>
                {partnerIdMessage || `Your ${formData.platform === 'zepto' ? 'Zepto' : 'Blinkit'} partner ID`}
              </div>
            </div>

            {/* Zone */}
            <div className="reg-field">
              <label className="reg-label">Dark Store Zone</label>

              <button type="button" className="reg-gps-btn" onClick={detectLocation}
                disabled={gpsStatus === 'loading' || zonesLoading}>
                {gpsStatus === 'loading'
                  ? <><span>⏳</span> Detecting location...</>
                  : <><span>📍</span> Detect My Zone</>}
              </button>

              {gpsStatus === 'success' && detectedZone && (
                <div className="reg-status success">✓ Detected: {detectedZone.zone.name} ({detectedZone.distance_km} km away)</div>
              )}
              {gpsStatus === 'too_far' && detectedZone && (
                <div className="reg-status warning">No zones near you. Nearest: {detectedZone.zone.name} ({detectedZone.distance_km} km). Select manually.</div>
              )}
              {gpsStatus === 'denied' && (
                <div className="reg-status warning">Location access denied. Select zone manually.</div>
              )}
              {gpsStatus === 'error' && (
                <div className="reg-status error">Could not detect location. Select zone manually.</div>
              )}

              <div className="reg-select-wrap">
                <select className="reg-input" name="zone_id" value={formData.zone_id}
                  onChange={handleChange} disabled={zonesLoading}>
                  {zonesLoading ? <option value="">Loading zones...</option>
                    : zones.length === 0 ? <option value="">No zones available — contact admin</option>
                      : <>
                        <option value="">Select your zone</option>
                        {zones.map((zone) => (
                          <option key={zone.id} value={zone.id}>
                            {zone.city} - {zone.name} ({zone.code})
                          </option>
                        ))}
                      </>
                  }
                </select>
              </div>

              <div className="reg-hint">
                {gpsStatus === 'success' ? 'Zone auto-detected. You can change it if needed.'
                  : gpsStatus === 'too_far' ? 'Select from available zones below'
                    : 'Use GPS detection or choose manually'}
              </div>
            </div>

            {error && <div className="reg-error">{error}</div>}

            <button type="submit" className="reg-btn"
              disabled={!formData.name || !formData.phone || loading}>
              {loading && <span className="spinner" />}
              Create Account
            </button>

          </form>
        </div>

        <div className="reg-footer">
          Already registered? <Link to="/login">Login here</Link>
        </div>

      </div>
    </>
  );
}