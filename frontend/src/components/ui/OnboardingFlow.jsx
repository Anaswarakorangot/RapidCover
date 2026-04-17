/**
 * OnboardingFlow.jsx
 * ─────────────────────────────────────────────
 * Wraps Slide 1 (RapidCoverOnboarding) and Slide 2 (RapidCoverOnboarding2)
 * with smooth swipe + button navigation.
 *
 * Usage in App.jsx:
 *   import OnboardingFlow from './components/ui/OnboardingFlow';
 *   <OnboardingFlow onFinish={() => navigate('/signup')} />
 *
 * Place this file alongside RapidCoverOnboarding.jsx and RapidCoverOnboarding2.jsx
 */

import { useState, useRef } from "react";
import RapidCoverOnboarding  from "./RapidCoverOnboarding";
import RapidCoverOnboarding2 from "./RapidCoverOnboarding2";

const flowStyles = `
  .flow-root {
    width: 100%;
    min-height: 100vh;
    overflow: hidden;
    position: relative;
  }

  .flow-track {
    display: flex;
    width: 200%;          /* 2 slides × 100% */
    min-height: 100vh;
    transition: transform 0.45s cubic-bezier(0.4, 0, 0.2, 1);
    will-change: transform;
  }

  .flow-track.no-transition {
    transition: none;
  }

  .flow-slide {
    width: 50%;           /* each slide = 100vw */
    min-height: 100vh;
    flex-shrink: 0;
    position: relative;
  }
`;

export default function OnboardingFlow({ onFinish, onLogin }) {
  const [currentSlide, setCurrentSlide] = useState(0); // 0 = slide1, 1 = slide2
  const trackRef     = useRef(null);
  const touchStartX  = useRef(null);
  const touchStartY  = useRef(null);
  const isDragging   = useRef(false);

  const goTo = (index) => {
    setCurrentSlide(Math.max(0, Math.min(1, index)));
  };

  /* ── Touch / swipe handlers ─────────────────── */
  const onTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX;
    touchStartY.current = e.touches[0].clientY;
    isDragging.current  = false;
  };

  const onTouchMove = (e) => {
    if (touchStartX.current === null) return;
    const dx = e.touches[0].clientX - touchStartX.current;
    const dy = e.touches[0].clientY - touchStartY.current;
    // Only hijack horizontal swipes
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 8) {
      isDragging.current = true;
      e.preventDefault(); // prevent page scroll
    }
  };

  const onTouchEnd = (e) => {
    if (!isDragging.current || touchStartX.current === null) return;
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    if (dx < -50 && currentSlide === 0) goTo(1); // swipe left → next
    if (dx >  50 && currentSlide === 1) goTo(0); // swipe right → prev
    touchStartX.current = null;
    isDragging.current  = false;
  };

  /* ── Mouse drag (desktop) ───────────────────── */
  const mouseStartX = useRef(null);

  const onMouseDown = (e) => { mouseStartX.current = e.clientX; };
  const onMouseUp   = (e) => {
    if (mouseStartX.current === null) return;
    const dx = e.clientX - mouseStartX.current;
    if (dx < -60 && currentSlide === 0) goTo(1);
    if (dx >  60 && currentSlide === 1) goTo(0);
    mouseStartX.current = null;
  };

  const translateX = currentSlide === 0 ? "0%" : "-50%";

  return (
    <>
      <style>{flowStyles}</style>

      <div
        className="flow-root"
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        onMouseDown={onMouseDown}
        onMouseUp={onMouseUp}
      >
        <div
          className="flow-track"
          ref={trackRef}
          style={{ transform: `translateX(${translateX})` }}
        >
          {/* ── Slide 1 ── */}
          <div className="flow-slide">
            <RapidCoverOnboarding
              onGetStarted={() => goTo(1)}   /* "Get Started" → slide 2 */
              onLogin={onLogin}
            />
          </div>

          {/* ── Slide 2 ── */}
          <div className="flow-slide">
            <RapidCoverOnboarding2
              onNext={onFinish}              /* final CTA → app callback */
            />
          </div>
        </div>
      </div>
    </>
  );
}
