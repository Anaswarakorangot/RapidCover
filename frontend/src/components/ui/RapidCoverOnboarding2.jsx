/**
 * RapidCoverOnboarding2.jsx
 * ─────────────────────────────────────────────
 * Second onboarding slide — stressed delivery partner in rain/storm.
 * Same layout as slide 1. Drop in after RapidCoverOnboarding.
 *
 * Usage:
 *   import RapidCoverOnboarding2 from './RapidCoverOnboarding2';
 *   <RapidCoverOnboarding2 onNext={() => navigate('/login')} />
 */

import { useState, useEffect } from "react";

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=DM+Sans:wght@400;500;600&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --blue-primary:  #2563eb;
    --blue-dark:     #1a4fcf;
    --blue-light:    #eff6ff;
    --orange:        #f97316;
    --green-primary: #3DB85C;
    --text-dark:     #1a1a2e;
    --text-mid:      #4a4a6a;
    --text-light:    #9a9ab8;
    --white:         #ffffff;
  }

  .rc2-screen {
    width: 100%;
    min-height: 100vh;
    background: var(--white);
    display: flex;
    flex-direction: column;
    font-family: 'DM Sans', sans-serif;
    overflow: hidden;
    position: relative;
  }

  .rc2-safe-top {
    height: env(safe-area-inset-top, 44px);
  }

  /* ── Logo ── */
  .rc2-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 20px 28px 0;
    opacity: 0;
    transform: translateY(-12px);
    animation: rc2FadeDown 0.6s ease 0.2s forwards;
  }

  .rc2-logo-icon {
    width: 42px;
    height: 42px;
    background: var(--blue-primary);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 4px 14px rgba(37,99,235,0.35);
  }

  .rc2-logo-text .brand {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 17px;
    color: var(--text-dark);
    line-height: 1.1;
  }

  .rc2-logo-text .sub {
    font-size: 10px;
    color: var(--text-light);
    font-weight: 500;
    letter-spacing: 0.3px;
    line-height: 1.4;
  }

  /* ── Hero ── */
  .rc2-hero {
    position: relative;
    flex: 1;
    min-height: 300px;
    max-height: 380px;
    margin-top: 8px;
    overflow: hidden;
  }

  .rc2-blob {
    position: absolute;
    top: -20px;
    right: -50px;
    width: 300px;
    height: 300px;
    background: radial-gradient(ellipse at 55% 45%, #bfdbfe 0%, #93c5fd 35%, transparent 65%);
    border-radius: 50%;
    pointer-events: none;
  }

  .rc2-blob2 {
    position: absolute;
    top: 60px;
    left: -30px;
    width: 180px;
    height: 180px;
    background: radial-gradient(ellipse at 45% 55%, #fde68a 0%, transparent 65%);
    border-radius: 50%;
    pointer-events: none;
    opacity: 0.5;
  }

  /* rain drops */
  .rc2-rain {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
  }

  .rc2-drop {
    position: absolute;
    width: 2px;
    border-radius: 2px;
    background: linear-gradient(to bottom, transparent, #93c5fd);
    animation: rc2Rain linear infinite;
    opacity: 0.55;
  }

  @keyframes rc2Rain {
    0%   { transform: translateY(-30px); opacity: 0; }
    10%  { opacity: 0.55; }
    90%  { opacity: 0.55; }
    100% { transform: translateY(380px); opacity: 0; }
  }

  /* partner illustration */
  .rc2-partner {
    position: absolute;
    right: 10px;
    top: 20px;
    width: 250px;
    opacity: 0;
    transform: translateX(40px);
    animation:
      rc2RideIn 0.9s cubic-bezier(0.22, 1, 0.36, 1) 0.4s forwards,
      rc2Shake  2.5s ease-in-out 1.6s infinite;
  }

  /* stats pill floating */
  .rc2-pill {
    position: absolute;
    left: 18px;
    top: 40px;
    background: var(--white);
    border-radius: 14px;
    padding: 8px 14px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    display: flex;
    align-items: center;
    gap: 8px;
    opacity: 0;
    transform: translateX(-20px);
    animation: rc2PillIn 0.7s ease 1s forwards;
  }

  .rc2-pill-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--orange);
    flex-shrink: 0;
    animation: rc2Pulse 1.2s ease-in-out 1.5s infinite;
  }

  .rc2-pill-text {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-dark);
    font-family: 'Nunito', sans-serif;
    white-space: nowrap;
  }

  .rc2-pill-text span {
    color: var(--orange);
  }

  /* credit pill */
  .rc2-credit {
    position: absolute;
    left: 18px;
    top: 110px;
    background: var(--white);
    border-radius: 14px;
    padding: 8px 14px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    display: flex;
    align-items: center;
    gap: 8px;
    opacity: 0;
    transform: translateX(-20px);
    animation: rc2PillIn 0.7s ease 1.3s forwards;
  }

  .rc2-credit-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--green-primary);
    flex-shrink: 0;
    animation: rc2Pulse 1.2s ease-in-out 1.8s infinite;
  }

  .rc2-credit-text {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-dark);
    font-family: 'Nunito', sans-serif;
    white-space: nowrap;
  }

  .rc2-credit-text span {
    color: var(--green-primary);
  }

  /* dots */
  .rc2-dots {
    position: absolute;
    left: 28px;
    bottom: 18px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .rc2-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #bfdbfe;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .rc2-dot.active {
    background: var(--blue-primary);
    height: 22px;
    border-radius: 4px;
  }

  /* ── Content ── */
  .rc2-content {
    padding: 24px 28px 0;
  }

  .rc2-tagline {
    font-family: 'Nunito', sans-serif;
    font-size: 28px;
    font-weight: 900;
    color: var(--text-dark);
    line-height: 1.2;
    margin-bottom: 12px;
    opacity: 0;
    transform: translateY(20px);
    animation: rc2FadeUp 0.7s ease 0.65s forwards;
  }

  .rc2-tagline span { color: var(--blue-primary); }

  .rc2-stats {
    display: flex;
    gap: 10px;
    margin-bottom: 18px;
    opacity: 0;
    transform: translateY(20px);
    animation: rc2FadeUp 0.7s ease 0.78s forwards;
  }

  .rc2-stat-card {
    flex: 1;
    background: var(--blue-light);
    border-radius: 14px;
    padding: 10px 12px;
  }

  .rc2-stat-num {
    font-family: 'Nunito', sans-serif;
    font-size: 18px;
    font-weight: 900;
    color: var(--blue-primary);
    line-height: 1;
  }

  .rc2-stat-label {
    font-size: 10px;
    color: var(--text-mid);
    margin-top: 3px;
    line-height: 1.3;
  }

  .rc2-description {
    font-size: 13.5px;
    color: var(--text-mid);
    line-height: 1.65;
    margin-bottom: 28px;
    opacity: 0;
    transform: translateY(20px);
    animation: rc2FadeUp 0.7s ease 0.88s forwards;
  }

  /* ── CTA ── */
  .rc2-btn {
    width: 100%;
    padding: 17px;
    background: var(--blue-primary);
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
    box-shadow: 0 8px 24px rgba(37,99,235,0.38);
    opacity: 0;
    animation: rc2FadeUp 0.7s ease 1.0s forwards;
  }

  .rc2-btn::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.18) 0%, transparent 55%);
    pointer-events: none;
    border-radius: inherit;
  }

  .rc2-btn:active {
    transform: scale(0.97);
    box-shadow: 0 4px 12px rgba(37,99,235,0.22);
  }

  /* ── Slide hint ── */
  .rc2-slide-hint {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 20px;
    margin-bottom: env(safe-area-inset-bottom, 28px);
    opacity: 0;
    animation: rc2FadeUp 0.7s ease 1.15s forwards;
  }

  .rc2-slide-hint .label {
    font-size: 12px;
    color: var(--text-light);
    font-weight: 500;
    letter-spacing: 0.5px;
  }

  .rc2-chevrons {
    display: flex;
    align-items: center;
    gap: 3px;
  }

  .rc2-chevrons i {
    display: block;
    width: 5px;
    height: 5px;
    border-right: 1.8px solid var(--blue-primary);
    border-bottom: 1.8px solid var(--blue-primary);
    transform: rotate(-45deg);
    font-style: normal;
  }

  .rc2-chevrons i:nth-child(1) { opacity: 0.35; }
  .rc2-chevrons i:nth-child(2) { opacity: 0.65; }
  .rc2-chevrons i:nth-child(3) { opacity: 1;    }

  /* ── Keyframes ── */
  @keyframes rc2FadeDown {
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes rc2FadeUp {
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes rc2RideIn {
    to { opacity: 1; transform: translateX(0); }
  }
  @keyframes rc2Shake {
    0%, 100% { transform: translateX(0) rotate(0deg); }
    20%       { transform: translateX(-3px) rotate(-1deg); }
    40%       { transform: translateX(2px) rotate(0.8deg); }
    60%       { transform: translateX(-2px) rotate(-0.5deg); }
    80%       { transform: translateX(1px) rotate(0.3deg); }
  }
  @keyframes rc2PillIn {
    to { opacity: 1; transform: translateX(0); }
  }
  @keyframes rc2Pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50%       { transform: scale(1.4); opacity: 0.7; }
  }
`;

/* Rain drops config */
const rainDrops = Array.from({ length: 18 }, (_, i) => ({
  left: `${5 + i * 5.2}%`,
  height: `${12 + (i % 5) * 6}px`,
  delay: `${(i * 0.18).toFixed(2)}s`,
  duration: `${0.8 + (i % 4) * 0.2}s`,
}));

/* ─── Stressed delivery partner SVG ─── */
const StressedPartnerIllustration = () => (
  <svg viewBox="0 0 260 280" fill="none" xmlns="http://www.w3.org/2000/svg">
    {/* shadow */}
    <ellipse cx="130" cy="268" rx="80" ry="9" fill="#00000015" />

    {/* puddle */}
    <ellipse cx="100" cy="245" rx="55" ry="8" fill="#bfdbfe" opacity="0.5" />
    <ellipse cx="100" cy="245" rx="38" ry="5" fill="#93c5fd" opacity="0.4" />

    {/* rear wheel */}
    <circle cx="68" cy="222" r="32" fill="#1e293b" />
    <circle cx="68" cy="222" r="24" fill="#334155" />
    <circle cx="68" cy="222" r="10" fill="#2563eb" />
    <circle cx="68" cy="222" r="4"  fill="#1e293b" />

    {/* front wheel */}
    <circle cx="196" cy="224" r="28" fill="#1e293b" />
    <circle cx="196" cy="224" r="20" fill="#334155" />
    <circle cx="196" cy="224" r="9"  fill="#2563eb" />
    <circle cx="196" cy="224" r="3"  fill="#1e293b" />

    {/* scooter body */}
    <path d="M76 192 Q88 155 128 152 L176 150 Q198 148 208 168 L216 192 Q196 202 128 202 Z" fill="#2563eb" />
    <path d="M76 192 Q70 212 68 224 L98 224 L98 197 Z" fill="#1a4fcf" />

    {/* handlebar */}
    <rect x="108" y="144" width="68" height="16" rx="8" fill="#1e293b" />
    <rect x="110" y="145" width="64" height="7"  rx="3" fill="#334155" />
    <line x1="198" y1="168" x2="196" y2="197" stroke="#1a4fcf" strokeWidth="7" strokeLinecap="round" />
    <rect x="193" y="143" width="38" height="7" rx="3" fill="#1e293b" />

    {/* footrest */}
    <rect x="80" y="200" width="48" height="6" rx="3" fill="#1a4fcf" />

    {/* delivery box — slightly tilted from storm */}
    <g transform="rotate(-4, 146, 113)">
      <rect x="118" y="90" width="56" height="50" rx="4" fill="#f97316" />
      <rect x="118" y="90" width="56" height="9"  rx="4" fill="#ea6c00" />
      <line x1="146" y1="90"  x2="146" y2="140" stroke="#ea6c00" strokeWidth="2.5" />
      <line x1="118" y1="109" x2="174" y2="109" stroke="#ea6c00" strokeWidth="2.5" />
      {/* wet patch on box */}
      <ellipse cx="132" cy="98" rx="6" ry="3" fill="#fed7aa" opacity="0.5" />
    </g>

    {/* rider body */}
    <path d="M133 190 Q126 178 118 173 L128 168 Q140 175 150 188 Z" fill="#fde68a" />
    <ellipse cx="150" cy="158" rx="19" ry="26" fill="#fcd34d" />

    {/* rain poncho / jacket */}
    <path d="M128 155 Q128 143 150 141 Q172 143 172 155 L168 182 Q150 186 132 182 Z" fill="#1d4ed8" />
    <path d="M132 157 Q150 154 162 157 L160 173 Q150 175 134 173 Z" fill="#2563eb" opacity="0.6" />

    {/* left arm gripping tight */}
    <path d="M128 158 Q112 154 110 148 Q110 140 117 141 Q124 143 128 150 Z" fill="#fde68a" />
    {/* right arm */}
    <path d="M170 155 Q182 150 185 147 L186 157 Q178 161 172 160 Z" fill="#fde68a" />

    {/* helmet — dark rainy style */}
    <circle cx="150" cy="122" r="24" fill="#1e293b" />
    <path d="M126 118 Q126 96 150 94 Q174 96 174 118 L170 124 Q150 130 130 124 Z" fill="#1e293b" />
    {/* visor */}
    <path d="M130 119 Q150 126 170 119 L168 125 Q150 130 132 125 Z" fill="#2563eb" opacity="0.7" />
    {/* helmet shine */}
    <path d="M133 105 Q142 100 155 103" stroke="#374151" strokeWidth="3" fill="none" strokeLinecap="round" opacity="0.6" />

    {/* face — worried expression */}
    <circle cx="150" cy="124" r="18" fill="#fde68a" />
    {/* worried brows */}
    <path d="M141 117 Q144 114 147 116" stroke="#78350f" strokeWidth="1.8" fill="none" strokeLinecap="round" />
    <path d="M153 116 Q156 114 159 117" stroke="#78350f" strokeWidth="1.8" fill="none" strokeLinecap="round" />
    {/* wide worried eyes */}
    <ellipse cx="144" cy="121" rx="2.5" ry="3" fill="#1e293b" />
    <ellipse cx="156" cy="121" rx="2.5" ry="3" fill="#1e293b" />
    {/* frown */}
    <path d="M145 130 Q150 127 155 130" stroke="#92400e" strokeWidth="1.8" fill="none" strokeLinecap="round" />
    {/* sweat drop */}
    <path d="M161 116 Q162 112 164 115 Q164 118 161 116Z" fill="#93c5fd" />

    {/* lightning bolt */}
    <path d="M22 60 L30 80 L24 80 L32 100 L18 76 L26 76 Z" fill="#fbbf24" opacity="0.9" />

    {/* rain lines (scene-level) */}
    <line x1="8"  y1="160" x2="14" y2="185" stroke="#93c5fd" strokeWidth="2"   strokeLinecap="round" opacity="0.5" />
    <line x1="18" y1="145" x2="24" y2="170" stroke="#93c5fd" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
    <line x1="28" y1="158" x2="34" y2="183" stroke="#93c5fd" strokeWidth="2"   strokeLinecap="round" opacity="0.45" />
    <line x1="38" y1="140" x2="44" y2="165" stroke="#93c5fd" strokeWidth="1.5" strokeLinecap="round" opacity="0.35" />
    <line x1="218" y1="140" x2="224" y2="165" stroke="#93c5fd" strokeWidth="2"   strokeLinecap="round" opacity="0.45" />
    <line x1="228" y1="155" x2="234" y2="180" stroke="#93c5fd" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
    <line x1="238" y1="148" x2="244" y2="173" stroke="#93c5fd" strokeWidth="2"   strokeLinecap="round" opacity="0.5" />
    <line x1="248" y1="160" x2="254" y2="185" stroke="#93c5fd" strokeWidth="1.5" strokeLinecap="round" opacity="0.35" />

    {/* cloud */}
    <circle cx="55"  cy="45" r="18" fill="#94a3b8" opacity="0.8" />
    <circle cx="75"  cy="35" r="22" fill="#94a3b8" opacity="0.85" />
    <circle cx="100" cy="38" r="19" fill="#94a3b8" opacity="0.8" />
    <circle cx="118" cy="46" r="15" fill="#94a3b8" opacity="0.75" />
    <rect x="50" y="46" width="80" height="20" rx="2" fill="#94a3b8" opacity="0.78" />

    {/* small rain from cloud */}
    <line x1="62"  y1="66" x2="58"  y2="82" stroke="#bfdbfe" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
    <line x1="75"  y1="66" x2="71"  y2="82" stroke="#bfdbfe" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
    <line x1="88"  y1="66" x2="84"  y2="82" stroke="#bfdbfe" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
    <line x1="101" y1="66" x2="97"  y2="82" stroke="#bfdbfe" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
    <line x1="114" y1="66" x2="110" y2="82" stroke="#bfdbfe" strokeWidth="2" strokeLinecap="round" opacity="0.7" />

    {/* ₹0 floating — income lost */}
    <rect x="185" y="55" width="52" height="26" rx="13" fill="#fee2e2" />
    <text x="211" y="73" textAnchor="middle" fontSize="13" fontWeight="800" fill="#dc2626" fontFamily="Nunito, sans-serif">₹0</text>

    {/* zone suspended tag */}
    <rect x="168" y="88" width="82" height="22" rx="11" fill="#fef3c7" />
    <text x="209" y="103" textAnchor="middle" fontSize="10" fontWeight="700" fill="#92400e" fontFamily="Nunito, sans-serif">Zone Suspended</text>
  </svg>
);

/* ─── Main component ─── */
export default function RapidCoverOnboarding2({ onNext }) {
  const [activeDot, setActiveDot] = useState(2);

  useEffect(() => {
    const t = setInterval(() => setActiveDot(d => (d % 3) + 1), 2400);
    return () => clearInterval(t);
  }, []);

  return (
    <>
      <style>{styles}</style>
      <div className="rc2-screen">

        <div className="rc2-safe-top" />

        {/* Logo */}
        <div className="rc2-logo">
          <div className="rc2-logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M3 12h3l3-9 4 18 3-9h5" stroke="white" strokeWidth="2.2"
                strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="rc2-logo-text">
            <div className="brand">RapidCover</div>
            <div className="sub">Parametric Income Intelligence</div>
          </div>
        </div>

        {/* Hero */}
        <div className="rc2-hero">
          <div className="rc2-blob" />
          <div className="rc2-blob2" />

          {/* animated rain drops */}
          <div className="rc2-rain">
            {rainDrops.map((d, i) => (
              <div
                key={i}
                className="rc2-drop"
                style={{
                  left: d.left,
                  height: d.height,
                  animationDelay: d.delay,
                  animationDuration: d.duration,
                }}
              />
            ))}
          </div>

          {/* floating pills */}
          <div className="rc2-pill">
            <div className="rc2-pill-dot" />
            <div className="rc2-pill-text">Zone BLR-047 <span>Suspended</span></div>
          </div>

          <div className="rc2-credit">
            <div className="rc2-credit-dot" />
            <div className="rc2-credit-text"><span>₹272 credited</span> in 49 sec</div>
          </div>

          {/* dots */}
          <div className="rc2-dots">
            {[1, 2, 3].map(i => (
              <div
                key={i}
                className={`rc2-dot${activeDot === i ? " active" : ""}`}
                onClick={() => setActiveDot(i)}
              />
            ))}
          </div>

          {/* illustration */}
          <div className="rc2-partner">
            <StressedPartnerIllustration />
          </div>
        </div>

        {/* Content */}
        <div className="rc2-content">
          <div className="rc2-tagline">
            When Zepto Stops,<br />
            <span>Your Income Doesn't.</span>
          </div>

          <div className="rc2-stats">
            <div className="rc2-stat-card">
              <div className="rc2-stat-num">₹0</div>
              <div className="rc2-stat-label">what platforms pay during zone suspension</div>
            </div>
            <div className="rc2-stat-card">
              <div className="rc2-stat-num">49s</div>
              <div className="rc2-stat-label">average time to UPI credit with RapidCover</div>
            </div>
            <div className="rc2-stat-card">
              <div className="rc2-stat-num">₹59</div>
              <div className="rc2-stat-label">per week — less than one chai a day</div>
            </div>
          </div>

          <p className="rc2-description">
            Rain, heatwave, AQI spike, curfew — if your zone shuts down, 
            RapidCover detects it automatically and credits your UPI 
            before you even reach home. Zero claim forms. Zero waiting.
          </p>

          <button className="rc2-btn" onClick={onNext}>
            Get My Cover — ₹59/week
          </button>

          <div className="rc2-slide-hint">
            <span className="label">Slide</span>
            <div className="rc2-chevrons">
              <i /><i /><i />
            </div>
          </div>
        </div>

      </div>
    </>
  );
}