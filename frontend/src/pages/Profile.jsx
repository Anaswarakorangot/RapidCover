import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardBody, Button, Input } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { NotificationToggle } from '../components/NotificationToggle';
import api from '../services/api';

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी (Hindi)' },
  { code: 'ta', label: 'தமிழ் (Tamil)' },
  { code: 'kn', label: 'ಕನ್ನಡ (Kannada)' },
  { code: 'te', label: 'తెలుగు (Telugu)' },
  { code: 'mr', label: 'मराठी (Marathi)' },
  { code: 'bn', label: 'বাংলা (Bengali)' },
];

// ─── UPI Validator ────────────────────────────────────────────
function validateUPI(upi) {
  return /^[\w.\-]{3,}@[\w]{3,}$/.test(upi.trim());
}

// ─── Aadhaar Validator (mock: 12 digits) ─────────────────────
function validateAadhaar(val) {
  return /^\d{12}$/.test(val.replace(/\s/g, ''));
}

// ─── PAN Validator ────────────────────────────────────────────
function validatePAN(val) {
  return /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(val.trim().toUpperCase());
}

// ─── UpiSetup Component ───────────────────────────────────────
function UpiSetup({ currentUpiId, onSave }) {
  const [editing, setEditing] = useState(false);
  const [upiId, setUpiId] = useState(currentUpiId || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const upiValid = upiId.trim() ? validateUPI(upiId) : null;

  async function handleSave() {
    if (!validateUPI(upiId)) { setError('Invalid UPI ID format'); return; }
    setSaving(true);
    setError('');
    try {
      await api.updateProfile({ upi_id: upiId.trim() });
      onSave?.(upiId.trim());
      setEditing(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div>
          {currentUpiId ? (
            <>
              <p style={{ fontWeight: 600, color: '#1a2e1a', fontSize: 14 }}>{currentUpiId}</p>
              <p style={{ fontSize: 12, color: '#3DB85C', marginTop: 2 }}>✓ UPI linked</p>
            </>
          ) : (
            <p style={{ fontSize: 13, color: '#8a9e8a', fontStyle: 'italic' }}>No UPI ID linked yet</p>
          )}
        </div>
        <Button variant="outline" onClick={() => setEditing(true)} style={{ flexShrink: 0 }}>
          {currentUpiId ? 'Change' : 'Add UPI'}
        </Button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ position: 'relative' }}>
        <input
          style={{
            width: '100%', padding: '12px 40px 12px 14px',
            border: `1.5px solid ${upiValid === false ? '#d97706' : upiValid === true ? '#3DB85C' : '#e2ece2'}`,
            borderRadius: 12, fontSize: 14, fontFamily: 'DM Sans, sans-serif',
            background: '#f7f9f7', outline: 'none', boxSizing: 'border-box',
          }}
          placeholder="yourname@upi"
          value={upiId}
          onChange={(e) => { setUpiId(e.target.value); setError(''); }}
        />
        {upiValid !== null && (
          <span style={{
            position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
            color: upiValid ? '#3DB85C' : '#d97706', fontSize: 14,
          }}>
            {upiValid ? '✓' : '✗'}
          </span>
        )}
      </div>
      <p style={{ fontSize: 11.5, color: upiValid === false ? '#d97706' : '#8a9e8a', marginTop: -4 }}>
        {upiValid === false ? 'Format: name@okaxis or phone@ybl'
          : upiValid === true ? 'Looks good!'
            : 'e.g. name@okaxis, phone@ybl'}
      </p>
      {error && <p style={{ fontSize: 12, color: '#dc2626', background: '#fef2f2', padding: '6px 10px', borderRadius: 8 }}>{error}</p>}
      <div style={{ display: 'flex', gap: 8 }}>
        <Button variant="secondary" style={{ flex: 1 }} onClick={() => { setEditing(false); setUpiId(currentUpiId || ''); setError(''); }}>
          Cancel
        </Button>
        <Button style={{ flex: 2 }} onClick={handleSave} loading={saving} disabled={!upiValid}>
          Save UPI
        </Button>
      </div>
    </div>
  );
}

// ─── KycSetup Component ───────────────────────────────────────
function KycSetup({ currentKyc, onSave }) {
  const [editing, setEditing] = useState(false);
  const [aadhaar, setAadhaar] = useState(currentKyc?.aadhaar_number || '');
  const [pan, setPan] = useState(currentKyc?.pan_number || '');
  const [aadhaarFile, setAadhaarFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const aadhaarValid = aadhaar.trim() ? validateAadhaar(aadhaar) : null;
  const panValid = pan.trim() ? validatePAN(pan) : null;

  const kycStatus = currentKyc?.kyc_status;
  const kycStatusDisplay = {
    verified: { label: '✓ KYC Verified', color: '#3DB85C', bg: '#e8f7ed' },
    pending: { label: '⏳ KYC Pending Review', color: '#d97706', bg: '#fef3c7' },
    failed: { label: '✗ KYC Failed', color: '#dc2626', bg: '#fef2f2' },
    skipped: { label: 'KYC not submitted', color: '#8a9e8a', bg: '#f7f9f7' },
  }[kycStatus || 'skipped'];

  async function handleSave() {
    if (aadhaar && !validateAadhaar(aadhaar)) { setError('Aadhaar must be 12 digits'); return; }
    if (pan && !validatePAN(pan)) { setError('Invalid PAN format (e.g. ABCDE1234F)'); return; }
    setSaving(true);
    setError('');
    try {
      await api.updateProfile({
        kyc: {
          aadhaar_number: aadhaar.replace(/\s/g, '') || null,
          pan_number: pan.toUpperCase() || null,
          kyc_status: aadhaar ? 'pending' : 'skipped',
        },
      });
      onSave?.({ aadhaar_number: aadhaar, pan_number: pan, kyc_status: aadhaar ? 'pending' : 'skipped' });
      setEditing(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{
            fontSize: 12, fontWeight: 700, padding: '4px 10px',
            borderRadius: 8, background: kycStatusDisplay.bg, color: kycStatusDisplay.color,
            fontFamily: 'Nunito, sans-serif',
          }}>
            {kycStatusDisplay.label}
          </span>
          <Button variant="outline" onClick={() => setEditing(true)}>
            {kycStatus === 'skipped' || !kycStatus ? 'Add KYC' : 'Update'}
          </Button>
        </div>
        {currentKyc?.aadhaar_number && (
          <p style={{ fontSize: 13, color: '#4a5e4a' }}>
            Aadhaar: ••••  ••••  {currentKyc.aadhaar_number.slice(-4)}
          </p>
        )}
        {currentKyc?.pan_number && (
          <p style={{ fontSize: 13, color: '#4a5e4a' }}>PAN: {currentKyc.pan_number}</p>
        )}
        <p style={{ fontSize: 11, color: '#8a9e8a' }}>🔒 Mock KYC — no real data stored</p>
      </div>
    );
  }

  const inputStyle = (valid) => ({
    width: '100%', padding: '12px 40px 12px 14px',
    border: `1.5px solid ${valid === false ? '#d97706' : valid === true ? '#3DB85C' : '#e2ece2'}`,
    borderRadius: 12, fontSize: 14, fontFamily: 'DM Sans, sans-serif',
    background: '#f7f9f7', outline: 'none', boxSizing: 'border-box',
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <p style={{ fontSize: 12, color: '#8a9e8a', background: '#fff8e1', border: '1px solid #f6cc3c', borderRadius: 8, padding: '6px 10px' }}>
        🔒 Mock KYC — fields are for demo only
      </p>

      {/* Aadhaar */}
      <div>
        <label style={{ fontSize: 12.5, fontWeight: 600, color: '#1a2e1a', display: 'block', marginBottom: 5, fontFamily: 'Nunito, sans-serif' }}>
          Aadhaar Number <span style={{ color: '#8a9e8a', fontWeight: 400 }}>(optional)</span>
        </label>
        <div style={{ position: 'relative' }}>
          <input
            style={inputStyle(aadhaarValid)}
            placeholder="1234 5678 9012"
            maxLength={14}
            value={aadhaar}
            onChange={(e) => { setAadhaar(e.target.value); setError(''); }}
          />
          {aadhaarValid !== null && (
            <span style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: aadhaarValid ? '#3DB85C' : '#d97706' }}>
              {aadhaarValid ? '✓' : '✗'}
            </span>
          )}
        </div>
        <p style={{ fontSize: 11.5, color: aadhaarValid === false ? '#d97706' : '#8a9e8a', marginTop: 4 }}>
          {aadhaarValid === false ? 'Must be 12 digits' : '12-digit Aadhaar number'}
        </p>
      </div>

      {/* PAN */}
      <div>
        <label style={{ fontSize: 12.5, fontWeight: 600, color: '#1a2e1a', display: 'block', marginBottom: 5, fontFamily: 'Nunito, sans-serif' }}>
          PAN Number <span style={{ color: '#8a9e8a', fontWeight: 400 }}>(optional)</span>
        </label>
        <div style={{ position: 'relative' }}>
          <input
            style={inputStyle(panValid)}
            placeholder="ABCDE1234F"
            maxLength={10}
            value={pan}
            onChange={(e) => { setPan(e.target.value.toUpperCase()); setError(''); }}
          />
          {panValid !== null && (
            <span style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: panValid ? '#3DB85C' : '#d97706' }}>
              {panValid ? '✓' : '✗'}
            </span>
          )}
        </div>
        <p style={{ fontSize: 11.5, color: panValid === false ? '#d97706' : '#8a9e8a', marginTop: 4 }}>
          {panValid === false ? 'Format: ABCDE1234F' : 'e.g. ABCDE1234F'}
        </p>
      </div>

      {/* File upload */}
      <div>
        <label style={{ fontSize: 12.5, fontWeight: 600, color: '#1a2e1a', display: 'block', marginBottom: 5, fontFamily: 'Nunito, sans-serif' }}>
          Upload Aadhaar <span style={{ color: '#8a9e8a', fontWeight: 400 }}>(optional)</span>
        </label>
        <label
          htmlFor="profileAadhaarFile"
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '12px 14px', border: `1.5px dashed ${aadhaarFile ? '#3DB85C' : '#e2ece2'}`,
            borderRadius: 12, background: aadhaarFile ? '#e8f7ed' : '#f7f9f7',
            cursor: 'pointer', fontSize: 13,
            color: aadhaarFile ? '#2a9e47' : '#4a5e4a',
          }}
        >
          <span>{aadhaarFile ? '✅' : '📎'}</span>
          <span>{aadhaarFile ? aadhaarFile.name : 'Tap to upload Aadhaar (image/PDF)'}</span>
        </label>
        <input
          id="profileAadhaarFile"
          type="file"
          accept="image/*,.pdf"
          style={{ display: 'none' }}
          onChange={(e) => setAadhaarFile(e.target.files[0] || null)}
        />
        <p style={{ fontSize: 11, color: '#8a9e8a', marginTop: 4 }}>JPEG, PNG or PDF · Mock upload</p>
      </div>

      {error && <p style={{ fontSize: 12, color: '#dc2626', background: '#fef2f2', padding: '6px 10px', borderRadius: 8 }}>{error}</p>}

      <div style={{ display: 'flex', gap: 8 }}>
        <Button variant="secondary" style={{ flex: 1 }} onClick={() => { setEditing(false); setError(''); }}>
          Cancel
        </Button>
        <Button style={{ flex: 2 }} onClick={handleSave} loading={saving}>
          Save KYC
        </Button>
      </div>
    </div>
  );
}

// ─── Main Profile Page ────────────────────────────────────────
export function Profile() {
  const navigate = useNavigate();
  const { user, logout, refreshUser } = useAuth();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user?.name || '');
  const [language, setLanguage] = useState(user?.language_pref || 'en');
  const [saving, setSaving] = useState(false);

  // Local state to reflect UPI/KYC updates without full page reload
  const [upiId, setUpiId] = useState(user?.upi_id || '');
  const [kyc, setKyc] = useState(user?.kyc || null);

  async function handleSave() {
    setSaving(true);
    try {
      await api.updateProfile({ name, language_pref: language });
      await refreshUser();
      setEditing(false);
    } catch (error) {
      alert(error.message);
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        <p className="text-gray-600">Manage your account</p>
      </div>

      {/* Profile Info */}
      <Card>
        <CardBody className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-2xl">👤</span>
            </div>
            <div>
              <p className="font-semibold text-gray-900">{user?.name}</p>
              <p className="text-sm text-gray-500">{user?.phone}</p>
              <p className="text-xs text-gray-400 capitalize">{user?.platform} Partner</p>
            </div>
          </div>

          {editing ? (
            <>
              <Input
                label="Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" className="flex-1" onClick={() => setEditing(false)}>
                  Cancel
                </Button>
                <Button className="flex-1" onClick={handleSave} loading={saving}>
                  Save
                </Button>
              </div>
            </>
          ) : (
            <Button variant="outline" className="w-full" onClick={() => setEditing(true)}>
              Edit Profile
            </Button>
          )}
        </CardBody>
      </Card>

      {/* Zone Info */}
      {user?.zone_id && (
        <Card>
          <CardBody>
            <h3 className="font-semibold text-gray-900 mb-2">Your Zone</h3>
            <p className="text-gray-600">Zone ID: {user.zone_id}</p>
          </CardBody>
        </Card>
      )}

      {/* ── UPI Linking ── */}
      <Card>
        <CardBody>
          <div style={{ marginBottom: 12 }}>
            <h3 className="font-semibold text-gray-900">💳 UPI Linking</h3>
            <p style={{ fontSize: 12, color: '#8a9e8a', marginTop: 2 }}>
              Link your UPI ID to receive claim payouts instantly
            </p>
          </div>
          <UpiSetup
            currentUpiId={upiId}
            onSave={(newUpi) => setUpiId(newUpi)}
          />
        </CardBody>
      </Card>

      {/* ── KYC Verification ── */}
      <Card>
        <CardBody>
          <div style={{ marginBottom: 12 }}>
            <h3 className="font-semibold text-gray-900">🪪 KYC Verification</h3>
            <p style={{ fontSize: 12, color: '#8a9e8a', marginTop: 2 }}>
              Complete KYC to unlock higher claim limits
            </p>
          </div>
          <KycSetup
            currentKyc={kyc}
            onSave={(newKyc) => setKyc(newKyc)}
          />
        </CardBody>
      </Card>

      {/* Notifications */}
      <Card>
        <CardBody>
          <h3 className="font-semibold text-gray-900 mb-2">Notifications</h3>
          <NotificationToggle />
        </CardBody>
      </Card>

      {/* Account Actions */}
      <Card>
        <CardBody className="space-y-3">
          <button className="w-full text-left py-2 text-gray-700 hover:text-gray-900 flex items-center justify-between">
            <span>📄 Terms of Service</span>
            <span className="text-gray-400">→</span>
          </button>
          <button className="w-full text-left py-2 text-gray-700 hover:text-gray-900 flex items-center justify-between">
            <span>🔒 Privacy Policy</span>
            <span className="text-gray-400">→</span>
          </button>
          <button className="w-full text-left py-2 text-gray-700 hover:text-gray-900 flex items-center justify-between">
            <span>💬 Help & Support</span>
            <span className="text-gray-400">→</span>
          </button>
        </CardBody>
      </Card>

      {/* Logout */}
      <Button variant="danger" className="w-full" onClick={handleLogout}>
        Logout
      </Button>

      <p className="text-center text-xs text-gray-400">
        RapidCover v1.0.0
      </p>
    </div>
  );
}