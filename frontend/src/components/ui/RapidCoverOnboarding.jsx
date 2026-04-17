/**
 * RapidCoverOnboarding.jsx
 * ─────────────────────────────────────────────
 * Clean onboarding screen — no phone frame, notch, or fake status bar.
 * Ready to drop into a React Native Web / Expo Web project.
 *
 * Dependencies:
 *   - React (useState, useEffect)
 *   - Google Fonts: Nunito + DM Sans (load in index.html or via expo-font)
 *
 * Usage:
 *   import RapidCoverOnboarding from './RapidCoverOnboarding';
 *   <RapidCoverOnboarding onGetStarted={() => navigation.navigate('Signup')} />
 */

import { useState, useEffect } from "react";

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
  }

  /* ── Root screen ─────────────────────────────── */
  .rc-screen {
    width: 100%;
    min-height: 100vh;
    background: var(--white);
    display: flex;
    flex-direction: column;
    font-family: 'DM Sans', sans-serif;
    overflow: hidden;
    position: relative;
  }

  /* ── Safe-area top padding (replaces status bar) */
  .rc-safe-top {
    height: env(safe-area-inset-top, 44px);
  }

  /* ── Logo ────────────────────────────────────── */
  .rc-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 20px 28px 0;
    opacity: 0;
    transform: translateY(-12px);
    animation: rcFadeDown 0.6s ease 0.2s forwards;
  }

  .rc-logo-icon {
    width: 42px;
    height: 42px;
    background: var(--green-primary);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 4px 14px rgba(61,184,92,0.35);
  }

  .rc-logo-text .brand {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 17px;
    color: var(--text-dark);
    line-height: 1.1;
  }

  .rc-logo-text .sub {
    font-size: 10px;
    color: var(--text-light);
    font-weight: 500;
    letter-spacing: 0.3px;
    line-height: 1.4;
  }

  /* ── Hero area ───────────────────────────────── */
  .rc-hero {
    position: relative;
    flex: 1;
    min-height: 300px;
    max-height: 380px;
    margin-top: 8px;
    overflow: hidden;
  }

  .rc-blob {
    position: absolute;
    top: -30px;
    right: -40px;
    width: 320px;
    height: 320px;
    background: radial-gradient(ellipse at 60% 40%, #c8f0d0 0%, #a8e4b8 38%, transparent 68%);
    border-radius: 50%;
    pointer-events: none;
  }

  .rc-road {
    position: absolute;
    bottom: 70px;
    left: 28px;
    right: 0;
    height: 2px;
    background: repeating-linear-gradient(
      to right,
      #d4ead6 0px, #d4ead6 16px,
      transparent 16px, transparent 28px
    );
    opacity: 0.7;
  }

  .rc-scooter {
    position: absolute;
    right: -8px;
    top: 10px;
    width: 270px;
    opacity: 0;
    transform: translateX(40px);
    animation:
      rcRideIn 0.9s cubic-bezier(0.22, 1, 0.36, 1) 0.4s forwards,
      rcFloat  3s ease-in-out 1.5s infinite;
  }

  /* ── Pagination dots ─────────────────────────── */
  .rc-dots {
    position: absolute;
    left: 28px;
    bottom: 18px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .rc-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #cde8d0;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .rc-dot.active {
    background: var(--green-primary);
    height: 22px;
    border-radius: 4px;
  }

  /* ── Content ─────────────────────────────────── */
  .rc-content {
    padding: 24px 28px 0;
  }

  .rc-tagline {
    font-family: 'Nunito', sans-serif;
    font-size: 28px;
    font-weight: 900;
    color: var(--text-dark);
    line-height: 1.2;
    margin-bottom: 12px;
    opacity: 0;
    transform: translateY(20px);
    animation: rcFadeUp 0.7s ease 0.65s forwards;
  }

  .rc-tagline span { color: var(--green-primary); }

  .rc-description {
    font-size: 13.5px;
    color: var(--text-mid);
    line-height: 1.65;
    margin-bottom: 32px;
    opacity: 0;
    transform: translateY(20px);
    animation: rcFadeUp 0.7s ease 0.8s forwards;
  }

  /* ── CTA button ──────────────────────────────── */
  .rc-btn {
    width: 100%;
    padding: 17px;
    background: var(--green-primary);
    border: none;
    border-radius: 18px;
    color: var(--white);
    font-family: 'Nunito', sans-serif;
    font-size: 17px;
    font-weight: 800;
    letter-spacing: 0.3px;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 8px 24px rgba(61,184,92,0.38);
    opacity: 0;
    animation: rcFadeUp 0.7s ease 0.95s forwards;
  }

  .rc-btn::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.18) 0%, transparent 55%);
    pointer-events: none;
    border-radius: inherit;
  }

  .rc-btn:active {
    transform: scale(0.97);
    box-shadow: 0 4px 12px rgba(61,184,92,0.22);
  }

  /* ── Slide hint ──────────────────────────────── */
  .rc-slide-hint {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 20px;
    margin-bottom: env(safe-area-inset-bottom, 28px);
    opacity: 0;
    animation: rcFadeUp 0.7s ease 1.1s forwards;
  }

  .rc-slide-hint .label {
    font-size: 12px;
    color: var(--text-light);
    font-weight: 500;
    letter-spacing: 0.5px;
  }

  .rc-chevrons {
    display: flex;
    align-items: center;
    gap: 3px;
  }

  .rc-chevrons i {
    display: block;
    width: 5px;
    height: 5px;
    border-right: 1.8px solid var(--green-primary);
    border-bottom: 1.8px solid var(--green-primary);
    transform: rotate(-45deg);
    font-style: normal;
  }

  .rc-chevrons i:nth-child(1) { opacity: 0.35; }
  .rc-chevrons i:nth-child(2) { opacity: 0.65; }
  .rc-chevrons i:nth-child(3) { opacity: 1;    }

  /* ── Keyframes ───────────────────────────────── */
  @keyframes rcFadeDown {
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes rcFadeUp {
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes rcRideIn {
    to { opacity: 1; transform: translateX(0); }
  }

  @keyframes rcFloat {
    0%, 100% { transform: translateY(0px);  }
    50%       { transform: translateY(-9px); }
  }
`;

/* ─── Scooter SVG (inline, no external assets) ────────────── */
const ScooterIllustration = () => (
  <svg viewBox="0 0 260 270" fill="none" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="130" cy="258" rx="90" ry="10" fill="#00000018" />
    <circle cx="70"  cy="220" r="34" fill="#2a2a2a" />
    <circle cx="70"  cy="220" r="26" fill="#444" />
    <circle cx="70"  cy="220" r="12" fill="#3DB85C" />
    <circle cx="70"  cy="220" r="5"  fill="#2a2a2a" />
    <circle cx="198" cy="222" r="30" fill="#2a2a2a" />
    <circle cx="198" cy="222" r="22" fill="#444" />
    <circle cx="198" cy="222" r="10" fill="#3DB85C" />
    <circle cx="198" cy="222" r="4"  fill="#2a2a2a" />
    <path d="M78 190 Q90 150 130 148 L180 145 Q200 144 210 165 L220 190 Q200 200 130 200 Z" fill="#3DB85C" />
    <path d="M78 190 Q72 210 70 222 L100 222 L100 195 Z" fill="#2a8a45" />
    <rect x="110" y="140" width="70" height="18" rx="9" fill="#2a2a2a" />
    <rect x="112" y="141" width="66" height="8"  rx="4" fill="#3a3a3a" />
    <line x1="200" y1="165" x2="198" y2="195" stroke="#2a8a45" strokeWidth="8" strokeLinecap="round" />
    <rect x="195" y="140" width="40" height="8" rx="4" fill="#2a2a2a" />
    <circle cx="234" cy="144" r="5" fill="#1a1a1a" />
    <rect x="82" y="198" width="50" height="7" rx="3" fill="#2a8a45" />
    <circle cx="220" cy="165" r="10" fill="#f5e642" opacity="0.9" />
    <circle cx="220" cy="165" r="6"  fill="#fff9c4" />
    <rect x="120" y="90" width="52" height="46" rx="4" fill="#f0a030" />
    <rect x="120" y="90" width="52" height="8"  rx="4" fill="#e08820" />
    <line x1="146" y1="90"  x2="146" y2="136" stroke="#e08820" strokeWidth="2.5" />
    <line x1="120" y1="108" x2="172" y2="108" stroke="#e08820" strokeWidth="2.5" />
    <path d="M135 188 Q128 175 120 170 L130 165 Q140 172 148 185 Z" fill="#f5c27a" />
    <ellipse cx="148" cy="155" rx="20" ry="28" fill="#f5c518" />
    <path d="M130 152 Q130 140 148 138 Q166 140 166 152 L162 178 Q148 182 134 178 Z" fill="#f5c518" />
    <path d="M138 155 Q148 152 158 155 L158 170 Q148 172 138 170 Z" fill="#fff" opacity="0.6" />
    <path d="M128 155 Q115 152 115 145 Q115 138 122 138 Q128 140 132 148 Z" fill="#f5c27a" />
    <path d="M168 152 Q180 148 185 145 L186 155 Q178 158 170 158 Z" fill="#f5c27a" />
    <circle cx="187" cy="143" r="7" fill="#3DB85C" />
    <circle cx="114" cy="143" r="6" fill="#3DB85C" />
    <circle cx="150" cy="122" r="22" fill="#f5c27a" />
    <path d="M128 118 Q128 96 150 96 Q172 96 172 118 L168 122 Q150 128 132 122 Z" fill="#3DB85C" />
    <path d="M128 118 Q128 112 150 112 Q172 112 172 118" stroke="#2a8a45" strokeWidth="2" fill="none" />
    <path d="M132 120 Q150 128 168 120" stroke="#2a9e47" strokeWidth="4" fill="none" strokeLinecap="round" />
    <circle cx="143" cy="122" r="2" fill="#3a2a1a" />
    <circle cx="157" cy="122" r="2" fill="#3a2a1a" />
    <path d="M145 128 Q150 132 155 128" stroke="#c0845a" strokeWidth="1.5" fill="none" strokeLinecap="round" />
    <path d="M132 122 Q130 132 128 138" stroke="#3a2010" strokeWidth="3" fill="none" strokeLinecap="round" />
    <path d="M133 124 Q128 136 126 142" stroke="#3a2010" strokeWidth="2" fill="none" strokeLinecap="round" />
    <line x1="10" y1="180" x2="45" y2="180" stroke="#3DB85C" strokeWidth="2.5" strokeLinecap="round" opacity="0.4" />
    <line x1="5"  y1="195" x2="50" y2="195" stroke="#3DB85C" strokeWidth="2"   strokeLinecap="round" opacity="0.3" />
    <line x1="15" y1="210" x2="48" y2="210" stroke="#3DB85C" strokeWidth="1.5" strokeLinecap="round" opacity="0.2" />
  </svg>
);

/* ─── Main component ───────────────────────────────────────── */
export default function RapidCoverOnboarding({ onGetStarted, onLogin }) {
  const [activeDot, setActiveDot] = useState(1);

  useEffect(() => {
    const t = setInterval(() => setActiveDot(d => (d % 3) + 1), 2400);
    return () => clearInterval(t);
  }, []);

  return (
    <>
      <style>{styles}</style>
      <div className="rc-screen">

        {/* Respects device safe-area — no fake status bar */}
        <div className="rc-safe-top" />

        {/* Logo */}
        <div className="rc-logo">
          <div className="rc-logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M3 12h3l3-9 4 18 3-9h5" stroke="white" strokeWidth="2.2"
                strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="rc-logo-text">
            <div className="brand">RapidCover</div>
            <div className="sub">Parametric Income Intelligence</div>
          </div>
        </div>

        {/* Hero */}
        <div className="rc-hero">
          <div className="rc-blob" />
          <div className="rc-road" />

          <div className="rc-dots">
            {[1, 2, 3].map(i => (
              <div
                key={i}
                className={`rc-dot${activeDot === i ? " active" : ""}`}
                onClick={() => setActiveDot(i)}
              />
            ))}
          </div>

          <div className="rc-scooter">
            <ScooterIllustration />
          </div>
        </div>

        {/* Content */}
        <div className="rc-content">
          <div className="rc-tagline">
            Protect Your Income.<br />
            <span>Deliver With Confidence.</span>
          </div>

          <p className="rc-description">
            India's first parametric insurance for Q-Commerce delivery partners.
            Stay covered against income loss from zone suspensions, floods, and more.
          </p>

          <button
            className="rc-btn"
            onClick={onGetStarted}
          >
            Get Started
          </button>

          {onLogin && (
            <div 
              style={{ textAlign: 'center', marginTop: 16, fontSize: 14.5, color: 'var(--green-dark)', fontWeight: 700, cursor: 'pointer', zIndex: 10, position: 'relative' }}
              onClick={onLogin}
            >
              Already have an account? Log in
            </div>
          )}

          <div className="rc-slide-hint">
            <span className="label">Slide</span>
            <div className="rc-chevrons">
              <i /><i /><i />
            </div>
          </div>
        </div>

      </div>
    </>
  );
}
