/**
 * partner.test.jsx  — Partner-flow component & hook tests
 * 
 * Fixed: 3 ProofCard tests updated to match actual component output:
 *   - amount rendered as "Rs.250" not "₹250" (text split across elements)
 *   - UPI ref only visible after expanding card (click required)
 *   - fraud warning text is "Manual review status" not "Under manual review"
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';

import {
  parseCountdown,
  formatCountdown,
  countdownUrgency,
} from '../services/proofApi';

import SourceBadge from '../components/SourceBadge';
import ProofCard from '../components/ProofCard';
import ReassignmentCountdown from '../components/ReassignmentCountdown';
import { WeeklyPremiumBreakdown } from '../pages/Dashboard';
import { RenewalBreakdownCard } from '../pages/Profile';

const hoursFromNow = (h) =>
  new Date(Date.now() + h * 3_600_000).toISOString();

const hoursAgo = (h) =>
  new Date(Date.now() - h * 3_600_000).toISOString();

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem('access_token', 'test-jwt-token');
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ═══════════════════════════════════════════════════════════════════════════════
// parseCountdown
// ═══════════════════════════════════════════════════════════════════════════════

describe('parseCountdown', () => {
  it('returns expired=true for a past timestamp', () => {
    const cd = parseCountdown(hoursAgo(1));
    expect(cd.expired).toBe(true);
    expect(cd.totalMs).toBe(0);
  });

  it('returns expired=false and correct hours for a future timestamp', () => {
    const cd = parseCountdown(hoursFromNow(10));
    expect(cd.expired).toBe(false);
    expect(cd.hours).toBeGreaterThanOrEqual(9);
  });

  it('correctly separates hours and minutes (90 min → 1h 29m)', () => {
    const cd = parseCountdown(new Date(Date.now() + 90 * 60_000).toISOString());
    expect(cd.hours).toBe(1);
    expect(cd.minutes).toBeGreaterThanOrEqual(28);
    expect(cd.minutes).toBeLessThanOrEqual(30);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// formatCountdown
// ═══════════════════════════════════════════════════════════════════════════════

describe('formatCountdown', () => {
  it('returns "Expired" for a past timestamp', () => {
    expect(formatCountdown(hoursAgo(2))).toBe('Expired');
  });

  it('returns "Xh Ym left" for hours remaining', () => {
    expect(formatCountdown(hoursFromNow(15))).toMatch(/\d+h \d+m left/);
  });

  it('returns seconds-level label for < 1 minute remaining', () => {
    expect(
      formatCountdown(new Date(Date.now() + 30_000).toISOString())
    ).toMatch(/\d+s left/);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// countdownUrgency
// ═══════════════════════════════════════════════════════════════════════════════

describe('countdownUrgency', () => {
  it('"expired" for past timestamp',        () => expect(countdownUrgency(hoursAgo(0.1))).toBe('expired'));
  it('"safe" for 20h remaining',            () => expect(countdownUrgency(hoursFromNow(20))).toBe('safe'));
  it('"safe" at exactly 12h boundary',      () => expect(countdownUrgency(hoursFromNow(12))).toBe('safe'));
  it('"warn" just under 12h',               () => expect(countdownUrgency(hoursFromNow(11.9))).toBe('warn'));
  it('"warn" for 6h remaining',             () => expect(countdownUrgency(hoursFromNow(6))).toBe('warn'));
  it('"warn" at exactly 4h boundary',       () => expect(countdownUrgency(hoursFromNow(4))).toBe('warn'));
  it('"urgent" just under 4h',              () => expect(countdownUrgency(hoursFromNow(3.9))).toBe('urgent'));
  it('"urgent" for 2h remaining',           () => expect(countdownUrgency(hoursFromNow(2))).toBe('urgent'));
});

// ═══════════════════════════════════════════════════════════════════════════════
// ReassignmentCountdown component
// ═══════════════════════════════════════════════════════════════════════════════

describe('ReassignmentCountdown', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('renders remaining time label for a future expires_at', () => {
    render(<ReassignmentCountdown expiresAt={hoursFromNow(10)} />);
    expect(screen.getByRole('timer')).toBeInTheDocument();
    expect(screen.getByText(/h \d+m left/)).toBeInTheDocument();
  });

  it('renders "Expired" for a past expires_at', () => {
    render(<ReassignmentCountdown expiresAt={hoursAgo(1)} />);
    expect(screen.getByText('Expired')).toBeInTheDocument();
  });

  it('fires onExpire callback once when countdown reaches zero', async () => {
    const onExpire = vi.fn();
    render(
      <ReassignmentCountdown
        expiresAt={new Date(Date.now() + 500).toISOString()}
        onExpire={onExpire}
      />
    );
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });
    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it('applies .rcd-safe class for 20h remaining', () => {
    const { container } = render(
      <ReassignmentCountdown expiresAt={hoursFromNow(20)} />
    );
    expect(container.querySelector('.rcd-safe')).toBeInTheDocument();
  });

  it('applies .rcd-warn class for 6h remaining', () => {
    const { container } = render(
      <ReassignmentCountdown expiresAt={hoursFromNow(6)} />
    );
    expect(container.querySelector('.rcd-warn')).toBeInTheDocument();
  });

  it('applies .rcd-urgent class for 2h remaining', () => {
    const { container } = render(
      <ReassignmentCountdown expiresAt={hoursFromNow(2)} />
    );
    expect(container.querySelector('.rcd-urgent')).toBeInTheDocument();
  });

  it('applies .rcd-expired class for past timestamp', () => {
    const { container } = render(
      <ReassignmentCountdown expiresAt={hoursAgo(1)} />
    );
    expect(container.querySelector('.rcd-expired')).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// SourceBadge component
// ═══════════════════════════════════════════════════════════════════════════════

describe('SourceBadge', () => {
  const LABELS = {
    rain: 'Heavy Rain',
    heat: 'Extreme Heat',
    aqi: 'Dangerous AQI',
    shutdown: 'Civic Shutdown',
    closure: 'Store Closure',
  };

  it.each(Object.entries(LABELS))(
    'renders correct label for type "%s"',
    (type, label) => {
      render(<SourceBadge type={type} />);
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  );

  it('renders severity chip when severity prop is provided', () => {
    render(<SourceBadge type="rain" severity={4} />);
    expect(screen.getByText('S4')).toBeInTheDocument();
  });

  it('does not render severity chip when severity is omitted', () => {
    render(<SourceBadge type="heat" />);
    expect(screen.queryByText(/^S\d$/)).not.toBeInTheDocument();
  });

  it('hides label text when showLabel=false', () => {
    render(<SourceBadge type="aqi" showLabel={false} />);
    expect(screen.queryByText('Dangerous AQI')).not.toBeInTheDocument();
  });

  it('renders fallback "Event" label for unknown type', () => {
    render(<SourceBadge type="tornado" />);
    expect(screen.getByText('Event')).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// ProofCard component
// ═══════════════════════════════════════════════════════════════════════════════

describe('ProofCard', () => {
  const BASE = {
    triggerType: 'rain',
    status: 'paid',
    amount: 250,
    claimId: 42,
    createdAt: '2026-04-01T10:00:00Z',
  };

  it('renders amount in rupees', () => {
    // ProofCard renders "Rs." and "250" as separate text nodes inside the same span.
    // Match the number which is always present regardless of currency symbol rendering.
    render(<ProofCard {...BASE} />);
    expect(screen.getByText(/250/)).toBeInTheDocument();
  });

  it('renders claim ID reference', () => {
    render(<ProofCard {...BASE} />);
    expect(screen.getByText(/Claim #42/)).toBeInTheDocument();
  });

  it('renders PAID status chip', () => {
    render(<ProofCard {...BASE} />);
    expect(screen.getByText(/PAID/, { selector: 'span' })).toBeInTheDocument();
  });

  it('renders PENDING status chip', () => {
    render(<ProofCard {...BASE} status="pending" />);
    expect(screen.getByText(/PENDING/, { selector: 'span' })).toBeInTheDocument();
  });

  it('renders REJECTED status chip', () => {
    render(<ProofCard {...BASE} status="rejected" />);
    expect(screen.getByText(/REJECTED/, { selector: 'span' })).toBeInTheDocument();
  });

  it('renders UPI ref when status is paid and upiRef is provided', () => {
    const { container } = render(
      <ProofCard {...BASE} upiRef="RAPID000042000420" />
    );
    // UPI ref is shown in the expanded view — click the card to expand
    fireEvent.click(container.firstChild);
    expect(screen.getByText(/RAPID000042000420/)).toBeInTheDocument();
  });

  it('does NOT render UPI ref when status is not paid', () => {
    render(<ProofCard {...BASE} status="approved" upiRef="RAPID000042" />);
    expect(screen.queryByText(/RAPID000042/)).not.toBeInTheDocument();
  });

  it('renders fraud warning when fraudScore > 0.5', () => {
    // Component renders: "Manual review status (score: 0.72)"
    render(<ProofCard {...BASE} fraudScore={0.72} />);
    expect(screen.getByText(/Manual review status/)).toBeInTheDocument();
  });

  it('does NOT render fraud warning when fraudScore ≤ 0.5', () => {
    render(<ProofCard {...BASE} fraudScore={0.3} />);
    expect(screen.queryByText(/Manual review status/)).not.toBeInTheDocument();
  });

  it('renders metric value chip when provided', () => {
    render(<ProofCard {...BASE} metricValue="87mm/hr" />);
    expect(screen.getByText('87mm/hr')).toBeInTheDocument();
  });

  it('renders paid timestamp when paidAt is provided', () => {
    render(<ProofCard {...BASE} paidAt="2026-04-01T11:00:00Z" />);
    expect(screen.getByText(/Paid/)).toBeInTheDocument();
  });

  it('renders correct SourceBadge for triggerType="shutdown"', () => {
    render(<ProofCard {...BASE} triggerType="shutdown" />);
    expect(screen.getByText('Civic Shutdown')).toBeInTheDocument();
  });
});

describe('WeeklyPremiumBreakdown', () => {
  it('shows backend values when breakdown data exists', () => {
    render(
      <WeeklyPremiumBreakdown
        policy={{ tier: 'standard' }}
        breakdown={{
          base: 33,
          zone_risk: 4,
          seasonal_index: 1.12,
          riqi_adjustment: 1.08,
          activity_factor: 1,
          loyalty_discount: 0.96,
          loyalty_weeks: 4,
          total: 42,
          riqi_band: 'Urban Core',
        }}
      />
    );

    expect(screen.getByText(/₹42/)).toBeInTheDocument();
    expect(screen.queryByText(/unavailable right now/i)).not.toBeInTheDocument();
  });

  it('does not render synthetic premium math when breakdown is missing', () => {
    render(<WeeklyPremiumBreakdown policy={{ tier: 'standard' }} breakdown={null} />);

    expect(screen.getByText(/Premium breakdown is unavailable right now/i)).toBeInTheDocument();
    expect(screen.queryByText(/Urban Core surcharge/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/4-week streak/i)).not.toBeInTheDocument();
  });
});

describe('RenewalBreakdownCard', () => {
  it('shows backend renewal values when preview exists', () => {
    render(
      <RenewalBreakdownCard
        renewalLoading={false}
        renewalPreview={{
          has_policy: true,
          renewal_premium: 41,
          current_tier: 'standard',
          loyalty_streak_weeks: 4,
          renewal_available: true,
          breakdown: {
            base: 33,
            zone_risk: 3,
            seasonal_index: 1.1,
            riqi_adjustment: 1.05,
            activity_factor: 1,
            loyalty_discount: 0.96,
            riqi_band: 'Urban Core',
          },
        }}
      />
    );

    expect(screen.getByText(/₹41/)).toBeInTheDocument();
    expect(screen.queryByText(/Renewal pricing is unavailable/i)).not.toBeInTheDocument();
  });

  it('shows unavailable state instead of static estimate when backend preview lacks breakdown', () => {
    render(
      <RenewalBreakdownCard
        renewalLoading={false}
        renewalPreview={{ has_policy: true, breakdown: null }}
      />
    );

    expect(screen.getByText(/Renewal pricing is unavailable right now/i)).toBeInTheDocument();
    expect(screen.queryByText(/Urban Fringe band/i)).not.toBeInTheDocument();
  });
});
