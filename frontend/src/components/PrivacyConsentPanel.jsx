/**
 * PrivacyConsentPanel.jsx  –  Transparency and data usage controls
 *
 * Person 3 Feature:
 *   - Explains Location, Activity, and Payout data usage
 *   - Professional plain-text UI
 *   - Mock toggles for judge interaction
 */

import { useState } from 'react';

const S = `
  .privacy-panel {
    font-family: 'DM Sans', sans-serif;
    color: #1a2e1a;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  .privacy-section {
    background: #f7f9f7;
    border: 1px solid #e2ece2;
    border-radius: 16px;
    padding: 16px;
  }
  .privacy-h3 {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    font-size: 15px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .privacy-p {
    font-size: 12.5px;
    line-height: 1.5;
    color: #4a5e4a;
    margin-bottom: 12px;
  }
  .privacy-toggle-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 12px;
    border-top: 1px dashed #e2ece2;
  }
  .toggle-label {
    font-size: 13px;
    font-weight: 600;
  }
  
  /* Simple Switch */
  .switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
  }
  .switch input { opacity: 0; width: 0; height: 0; }
  .slider {
    position: absolute;
    cursor: pointer;
    top: 0; left: 0; right: 0; bottom: 0;
    background-color: #cbd5e1;
    transition: .4s;
    border-radius: 34px;
  }
  .slider:before {
    position: absolute;
    content: "";
    height: 18px; width: 18px;
    left: 3px; bottom: 3px;
    background-color: white;
    transition: .4s;
    border-radius: 50%;
  }
  input:checked + .slider { background-color: #3DB85C; }
  input:checked + .slider:before { transform: translateX(20px); }
`;

export default function PrivacyConsentPanel() {
  const [consents, setConsents] = useState({
    location: true,
    activity: true,
    notifications: true,
    payouts: true
  });

  const toggle = (key) => setConsents(prev => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="privacy-panel">
      <style>{S}</style>
      
      <div className="privacy-section">
        <h3 className="privacy-h3">Location Services</h3>
        <p className="privacy-p">
          RapidCover uses your GPS data exclusively to verify your presence in assigned risk zones during active disruptions. We do not track your location when you are off-shift or outside impact windows.
        </p>
        <div className="privacy-toggle-row">
          <span className="toggle-label">Active Zone Verification</span>
          <label className="switch">
            <input type="checkbox" checked={consents.location} onChange={() => toggle('location')} />
            <span className="slider"></span>
          </label>
        </div>
      </div>

      <div className="privacy-section">
        <h3 className="privacy-h3">Activity Validation</h3>
        <p className="privacy-p">
          We correlate your platform provider data (orders/tasks) with weather events to ensure fair payouts for active workers. This data is pseudonymized and stored for 30 days.
        </p>
        <div className="privacy-toggle-row">
          <span className="toggle-label">Sync Platform Activity</span>
          <label className="switch">
            <input type="checkbox" checked={consents.activity} onChange={() => toggle('activity')} />
            <span className="slider"></span>
          </label>
        </div>
      </div>

      <div className="privacy-section">
        <h3 className="privacy-h3">Payout Data</h3>
        <p className="privacy-p">
          Your UPI ID and Bank details are stored securely using industry-standard encryption to facilitate instant transfers. RapidCover never has access to your account balance or history.
        </p>
        <div className="privacy-toggle-row">
          <span className="toggle-label">Secure Payout Storage</span>
          <label className="switch">
            <input type="checkbox" checked={consents.payouts} onChange={() => toggle('payouts')} />
            <span className="slider"></span>
          </label>
        </div>
      </div>

      <div className="privacy-section" style={{ background: '#e8f7ed', borderColor: '#3DB85C' }}>
        <h3 className="privacy-h3" style={{ color: '#2a9e47' }}>Our Commitment</h3>
        <p className="privacy-p" style={{ marginBottom: 0 }}>
          RapidCover is GDPR and Digital Personal Data Protection (DPDP) compliant. We never sell your data to third-party marketplaces.
        </p>
      </div>
    </div>
  );
}
