/**
 * Login.jsx  –  Partner login with OTP
 *
 * Person 1 Phase 2 (Task 6 – demo UX cleanup):
 *   - Dev OTP display is small, labelled "DEV ONLY", non-intrusive
 *   - Mock KYC note is secondary text only
 *   - Main user journey feels real even though OTP is mocked
 *
 * UI: Original green theme restored (matching Register.jsx design system).
 * Auth flow: Uses api.requestOtp / api.verifyOtp directly + login(token).
 */

import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useAdminAuth } from '../context/AdminAuthContext';

const styles = `
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
    --error:         #dc2626;
  }

  .login-screen {
    width: 100%;
    min-height: 100vh;
    background: var(--white);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: 'DM Sans', sans-serif;
    padding: 32px 28px;
  }

  .login-logo {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 36px;
  }
  .login-logo-icon {
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
  .login-logo-brand {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 22px;
    color: var(--text-dark);
    line-height: 1.1;
  }
  .login-logo-sub {
    font-size: 11px;
    color: var(--text-light);
    font-weight: 500;
    letter-spacing: 0.4px;
    margin-top: 3px;
  }

  .login-card {
    width: 100%;
    max-width: 360px;
    background: var(--white);
    border-radius: 24px;
    padding: 28px 24px;
    box-shadow: 0 4px 32px rgba(0,0,0,0.08);
  }

  .login-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 24px;
    color: var(--text-dark);
    margin-bottom: 6px;
  }
  .login-subtitle {
    font-size: 13px;
    color: var(--text-mid);
    line-height: 1.5;
    margin-bottom: 24px;
  }

  .login-field { margin-bottom: 16px; }
  .login-label {
    font-size: 12.5px;
    font-weight: 600;
    color: var(--text-dark);
    margin-bottom: 6px;
    display: block;
    font-family: 'Nunito', sans-serif;
  }

  .login-input {
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
  }
  .login-input::placeholder { color: #b8c8b8; }
  .login-input:focus {
    border-color: var(--green-primary);
    box-shadow: 0 0 0 3px rgba(61,184,92,0.12);
    background: var(--white);
  }
  .login-input.error { border-color: var(--error); }

  .login-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
  }
  .login-remember {
    display: flex;
    align-items: center;
    gap: 7px;
    cursor: pointer;
  }
  .login-checkbox {
    width: 16px;
    height: 16px;
    accent-color: var(--green-primary);
    cursor: pointer;
  }
  .login-remember-label {
    font-size: 12.5px;
    color: var(--text-mid);
    user-select: none;
  }

  .login-btn {
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
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 8px 22px rgba(61,184,92,0.38);
    margin-bottom: 18px;
  }
  .login-btn::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.18) 0%, transparent 55%);
    pointer-events: none;
    border-radius: inherit;
  }
  .login-btn:active   { transform: scale(0.97); }
  .login-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

  .login-btn .spinner {
    display: inline-block;
    width: 16px; height: 16px;
    border: 2px solid rgba(255,255,255,0.4);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    vertical-align: middle;
    margin-right: 8px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .login-error {
    font-size: 12.5px;
    color: var(--error);
    margin-bottom: 12px;
    text-align: center;
  }

  .dev-otp-box {
    margin-bottom: 16px;
    padding: 12px 14px;
    background: #fefce8;
    border: 1.5px solid #fde68a;
    border-radius: 14px;
  }
  .dev-otp-label { font-size: 11px; color: #92400e; margin-bottom: 4px; }
  .dev-otp-value {
    font-size: 26px;
    font-family: monospace;
    font-weight: 800;
    color: #78350f;
    letter-spacing: 4px;
  }

  .login-otp-info {
    font-size: 13px;
    color: var(--text-mid);
    margin-bottom: 20px;
  }
  .login-otp-info strong { color: var(--text-dark); }

  .login-otp-input {
    width: 100%;
    padding: 14px 16px;
    border: 1.5px solid var(--border);
    border-radius: 14px;
    font-size: 22px;
    font-family: monospace;
    font-weight: 800;
    color: var(--text-dark);
    background: var(--gray-bg);
    outline: none;
    text-align: center;
    letter-spacing: 6px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    margin-bottom: 16px;
  }
  .login-otp-input:focus {
    border-color: var(--green-primary);
    box-shadow: 0 0 0 3px rgba(61,184,92,0.12);
    background: var(--white);
  }

  .login-back {
    width: 100%;
    padding: 12px;
    background: none;
    border: 1.5px solid var(--border);
    border-radius: 14px;
    font-size: 13.5px;
    color: var(--text-mid);
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    transition: border-color 0.2s ease, color 0.2s ease;
  }
  .login-back:hover { border-color: var(--green-primary); color: var(--green-primary); }

  .login-footer {
    margin-top: 24px;
    font-size: 13px;
    color: var(--text-mid);
    text-align: center;
  }
  .login-footer a {
    color: var(--green-primary);
    font-weight: 700;
    text-decoration: none;
    font-family: 'Nunito', sans-serif;
  }

  .login-mock-note {
    text-align: center;
    font-size: 11px;
    color: #ccc;
    margin-top: 14px;
  }

  .login-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0;
  }
  .login-divider::before,
  .login-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }
  .login-divider-text {
    font-size: 11px;
    color: var(--text-light);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
`;

export default function Login() {
  const { login } = useAuth();
  const { login: adminLogin } = useAdminAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const adminMode = searchParams.get('admin') === '1';
  const adminNext = searchParams.get('next') || '/admin';

  const [step, setStep] = useState('phone');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [devOtp, setDevOtp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleRequestOTP(e) {
    e.preventDefault();
    setError('');

    // Admin login if email is filled
    if (email.trim()) {
      if (!password.trim()) {
        setError('Please enter your admin password.');
        return;
      }
      setLoading(true);
      try {
        await adminLogin(email.trim(), password.trim());
        navigate(adminNext);
      } catch (err) {
        setError(err.message || 'Invalid admin credentials');
      } finally {
        setLoading(false);
      }
      return;
    }

    if (adminMode) {
      setError('Enter your admin email and password to continue to the admin panel.');
      return;
    }

    // Partner OTP login if phone is filled
    if (!phone.trim()) {
      setError('Please enter your phone number or admin email.');
      return;
    }
    setLoading(true);
    try {
      const result = await api.requestOtp(phone.trim());
      if (result?.otp) {
        setDevOtp(result.otp);
      }
      setStep('otp');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOTP(e) {
    e.preventDefault();
    setError('');
    if (!otp.trim()) { setError('Please enter the OTP.'); return; }
    setLoading(true);
    try {
      await login(phone.trim(), otp.trim());
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <style>{styles}</style>
      <div className="login-screen">

        {/* Logo */}
        <div className="login-logo">
          <div className="login-logo-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M3 12h3l3-9 4 18 3-9h5" stroke="white" strokeWidth="2.2"
                strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="login-logo-brand">RapidCover</div>
          <div className="login-logo-sub">Parametric Income Intelligence</div>
        </div>

        {/* Card */}
        <div className="login-card">

          {step === 'phone' ? (
            <form onSubmit={handleRequestOTP}>
              <div className="login-title">Login</div>
              <div className="login-subtitle">
                {adminMode
                  ? 'Admin access requires email and password.'
                  : 'Enter your phone number to receive an OTP.'}
              </div>

              {!adminMode && (
                <>
                  <div className="login-field">
                    <label className="login-label">Phone Number</label>
                    <input
                      className={`login-input${error && !email ? ' error' : ''}`}
                      type="tel"
                      inputMode="numeric"
                      placeholder="+91 9876543210"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                      autoFocus={!email}
                    />
                  </div>

                  <div className="login-divider">
                    <div className="login-divider-text">OR</div>
                  </div>
                </>
              )}

              {adminMode && (
                <div className="login-field">
                  <label className="login-label">Admin Email</label>
                  <input
                    className={`login-input${error && email ? ' error' : ''}`}
                    type="email"
                    placeholder="admin@rapidcover.in"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoFocus
                  />
                </div>
              )}

              {adminMode && (
                <div className="login-field">
                  <label className="login-label">Password</label>
                  <input
                    className={`login-input${error && email ? ' error' : ''}`}
                    type="password"
                    placeholder="Enter admin password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
              )}

              {error && <div className="login-error">{error}</div>}

              <div className="login-row">
                <label className="login-remember">
                  <input type="checkbox" className="login-checkbox" />
                  <span className="login-remember-label">Remember Me</span>
                </label>
              </div>

              <button
                type="submit"
                className="login-btn"
                disabled={((!adminMode && phone.length < 10) || (adminMode && (!email || !password))) || loading}
              >
                {loading && <span className="spinner" />}
                {adminMode ? 'Admin Login' : 'Get OTP'}
              </button>

              <div className="login-footer">
                New here?{' '}
                <a href="/register">Register now</a>
              </div>
            </form>

          ) : (
            <form onSubmit={handleVerifyOTP}>
              <div className="login-title">Enter OTP</div>
              <div className="login-otp-info">
                Sent to <strong>{phone}</strong>
              </div>

              {/* Dev OTP – small, labelled, secondary – does NOT dominate the UI */}
              {devOtp && (
                <div className="dev-otp-box">
                  <div className="dev-otp-label">DEV ONLY — Your OTP:</div>
                  <div className="dev-otp-value">{devOtp}</div>
                </div>
              )}

              <input
                className="login-otp-input"
                type="text"
                inputMode="numeric"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="••••••"
                autoFocus
                maxLength={6}
              />

              {error && <div className="login-error" style={{ marginTop: 10 }}>{error}</div>}

              <button
                type="submit"
                className="login-btn"
                style={{ marginTop: 20 }}
                disabled={otp.length < 4 || loading}
              >
                {loading && <span className="spinner" />}
                Verify &amp; Login
              </button>

              <button
                type="button"
                className="login-back"
                onClick={() => { setStep('phone'); setOtp(''); setDevOtp(null); }}
              >
                ← Change phone number
              </button>

              {/* Mock KYC note – small, non-breaking, secondary */}
              <p className="login-mock-note">
                KYC verification is mocked for this demo.
              </p>
            </form>
          )}
        </div>

      </div>
    </>
  );
}
