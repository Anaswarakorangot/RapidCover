// frontend/src/components/StressWidget.jsx
// Hardcoded stress scenario table — all 6 actuarial scenarios from Section 4 of team guide
import { useState } from 'react';

const SCENARIOS = [
    {
        id: 'S1',
        name: '14-Day Monsoon',
        cities: 'BLR + BOM',
        partners: 4200,
        payout: '₹82.32L',
        payoutRaw: 8232000,
        poolPct: '~190%',
        mode: 'Day 5: Sustained Event - 70% payout mode. Day 7: Reinsurance flagged. City cap 120% - Reinsurance activation.',
        badge: 'reinsurance',
        detail: {
            blr: { partners: 1800, payout: '₹35.28L', calc: '1,800 x 14d x Rs.280/d @70% of Rs.400' },
            bom: { partners: 2400, payout: '₹47.04L', calc: '2,400 x 14d x Rs.280/d @70% of Rs.400' },
            note: 'Days 1-4: Normal mode (Rs.400/d Standard max). Day 5+: Sustained Event flag - 70% payout (Rs.280/d), no weekly cap, max 21 days.',
        },
    },
    {
        id: 'S2',
        name: 'AQI Spike',
        cities: 'DEL + NOI + GGN',
        partners: 5100,
        payout: '₹81.6L',
        payoutRaw: 8160000,
        poolPct: '~180%',
        mode: 'Day 5: Sustained Event flag. Proportional reduction via zone pool share cap. Each city loss ratio monitored independently.',
        badge: 'reinsurance',
        detail: {
            del: { partners: 3200, payout: '₹51.2L', calc: '3,200 x 5d x Rs.400 @70% = Rs.280 (sustained from day 5)' },
            noi: { partners: 1900, payout: '₹30.4L', calc: '1,900 x 5d x Rs.400 @70% = Rs.280 (sustained from day 5)' },
            note: 'Ward-level trigger data applies — Anand Vihar AQI does not auto-trigger Dwarka. Each ward threshold checked independently.',
        },
    },
    {
        id: 'S3',
        name: 'Cyclone',
        cities: 'CHN + BOM',
        partners: 6000,
        payout: '₹90L',
        payoutRaw: 0000,
        poolPct: '~320%',
        mode: 'Reinsurance activation on Day 1 (Loss Ratio immediately exceeds 100%). City payout capped at 120% of weekly pool.',
        badge: 'catastrophic',
        detail: {
            chn: { partners: 2200, payout: '₹33L', calc: '2,200 x 3d x Rs.500 (Pro max)' },
            bom: { partners: 3800, payout: '₹57L', calc: '3,800 x 3d x Rs.500 (Pro max)' },
            note: 'Catastrophic event. Reinsurance treaty activates immediately. Partners receive proportional reduction via zone_pool_share formula.',
        },
    },
    {
        id: 'S4',
        name: 'State Bandh',
        cities: 'All zones',
        partners: 3500,
        payout: '₹42L',
        payoutRaw: 4200000,
        poolPct: '~97%',
        mode: 'Normal payout Days 1-2. Day 3: Proportional reduction if pool approaches cap. Active shift check filters partners on leave.',
        badge: 'proportional',
        detail: {
            note: '~3,500 active partners (excluding those on declared leave or voluntarily offline). Day 3 triggers proportional reduction. Reinsurance review flagged. Govt policy exclusion does NOT apply — bandh is operational disruption, not regulatory override.',
        },
    },
    {
        id: 'S5',
        name: 'Dark Store Mass Closure',
        cities: 'BLR (40% stores)',
        partners: 700,
        payout: '₹2.8L',
        payoutRaw: 280000,
        poolPct: '~18%',
        mode: 'Normal payout Day 1. Zone reassignment protocol activated: 24h acceptance window, premium recalculated for remaining days.',
        badge: 'normal',
        detail: {
            note: 'FSSAI regulatory order closes 40% of Bangalore dark stores. Direct trigger is store closure (covered), not government policy change. Zone reassignment history logged in partner profile.',
        },
    },
    {
        id: 'S6',
        name: 'Collusion Ring',
        cities: '50 fake accounts, same zone',
        partners: 50,
        payout: '₹0',
        payoutRaw: 0,
        poolPct: '8% (if missed)',
        mode: 'Auto-reject + Fraud queue. Expected: 35–40 accounts auto-rejected (score >0.90), 10–15 to manual queue (0.75–0.90).',
        badge: 'fraud',
        detail: {
            signals: [
                'device_fingerprint_match (w5) — shared/emulated devices',
                'centroid_drift_score (w7) — no 30-day GPS history',
                'claim_frequency_score (w4) — newly registered accounts spike',
                'gps_coherence (w1) — fails for GPS-spoofed accounts',
            ],
            note: 'Admin fraud queue shows cluster pattern — all 50 claims from same event, same zone, same device profile. Bulk-reject available.',
        },
    },
];

const BADGE_STYLES = {
    reinsurance: { bg: '#fff3cd', color: '#856404', label: 'Reinsurance' },
    catastrophic: { bg: '#f8d7da', color: '#842029', label: 'Catastrophic' },
    proportional: { bg: '#cff4fc', color: '#0a6170', label: 'Proportional' },
    normal: { bg: '#d1e7dd', color: '#0f5132', label: 'Normal' },
    fraud: { bg: '#e2d9f3', color: '#432874', label: 'Fraud Blocked' },
};

export default function StressWidget() {
    const [expanded, setExpanded] = useState(null);

    function toggle(id) {
        setExpanded(prev => (prev === id ? null : id));
    }

    return (
        <section className="stress-widget">
            <div className="stress-widget__header">
                <div>
                    <h2 className="stress-widget__title">⚡ Stress Scenarios</h2>
                    <p className="stress-widget__subtitle">
                        Actuarial stress test — 6 scenarios modelling extreme but plausible events
                    </p>
                </div>
                <span className="stress-widget__count">{SCENARIOS.length} scenarios</span>
            </div>

            {/* Summary table */}
            <div className="stress-table-wrapper">
                <table className="stress-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Scenario</th>
                            <th>Cities</th>
                            <th className="stress-table__num">Partners</th>
                            <th className="stress-table__num">Est. Payout</th>
                            <th className="stress-table__num">% Weekly Pool</th>
                            <th>System Mode</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {SCENARIOS.map(s => {
                            const badge = BADGE_STYLES[s.badge];
                            const isOpen = expanded === s.id;
                            return (
                                <>
                                    <tr key={s.id} className={`stress-table__row ${isOpen ? 'stress-table__row--open' : ''}`}>
                                        <td><code className="stress-id">{s.id}</code></td>
                                        <td className="stress-table__name">{s.name}</td>
                                        <td className="stress-table__cities">{s.cities}</td>
                                        <td className="stress-table__num">{s.partners.toLocaleString()}</td>
                                        <td className="stress-table__num stress-table__payout">{s.payout}</td>
                                        <td className="stress-table__num">
                                            <span
                                                className="stress-pool-badge"
                                                style={{ background: badge.bg, color: badge.color }}
                                            >
                                                {s.poolPct}
                                            </span>
                                        </td>
                                        <td>
                                            <span
                                                className="stress-mode-badge"
                                                style={{ background: badge.bg, color: badge.color }}
                                            >
                                                {badge.label}
                                            </span>
                                        </td>
                                        <td>
                                            <button
                                                className="stress-expand-btn"
                                                onClick={() => toggle(s.id)}
                                                aria-label={isOpen ? 'Collapse' : 'Expand'}
                                            >
                                                {isOpen ? '▲' : '▼'}
                                            </button>
                                        </td>
                                    </tr>
                                    {isOpen && (
                                        <tr key={`${s.id}-detail`} className="stress-detail-row">
                                            <td colSpan={8}>
                                                <div className="stress-detail">
                                                    <p className="stress-detail__mode"><strong>System Response:</strong> {s.mode}</p>

                                                    {/* City breakdown for multi-city scenarios */}
                                                    {s.detail.blr && (
                                                        <div className="stress-detail__cities">
                                                            <div className="stress-detail__city">
                                                                <span className="stress-detail__city-name">Bangalore</span>
                                                                <span>{s.detail.blr.partners.toLocaleString()} partners</span>
                                                                <span>{s.detail.blr.payout}</span>
                                                                <code>{s.detail.blr.calc}</code>
                                                            </div>
                                                            <div className="stress-detail__city">
                                                                <span className="stress-detail__city-name">Mumbai</span>
                                                                <span>{s.detail.bom.partners.toLocaleString()} partners</span>
                                                                <span>{s.detail.bom.payout}</span>
                                                                <code>{s.detail.bom.calc}</code>
                                                            </div>
                                                        </div>
                                                    )}
                                                    {s.detail.del && (
                                                        <div className="stress-detail__cities">
                                                            <div className="stress-detail__city">
                                                                <span className="stress-detail__city-name">Delhi</span>
                                                                <span>{s.detail.del.partners.toLocaleString()} partners</span>
                                                                <span>{s.detail.del.payout}</span>
                                                                <code>{s.detail.del.calc}</code>
                                                            </div>
                                                            <div className="stress-detail__city">
                                                                <span className="stress-detail__city-name">Noida + Gurugram</span>
                                                                <span>{s.detail.noi.partners.toLocaleString()} partners</span>
                                                                <span>{s.detail.noi.payout}</span>
                                                                <code>{s.detail.noi.calc}</code>
                                                            </div>
                                                        </div>
                                                    )}
                                                    {s.detail.chn && (
                                                        <div className="stress-detail__cities">
                                                            <div className="stress-detail__city">
                                                                <span className="stress-detail__city-name">Chennai</span>
                                                                <span>{s.detail.chn.partners.toLocaleString()} partners</span>
                                                                <span>{s.detail.chn.payout}</span>
                                                                <code>{s.detail.chn.calc}</code>
                                                            </div>
                                                            <div className="stress-detail__city">
                                                                <span className="stress-detail__city-name">Mumbai</span>
                                                                <span>{s.detail.bom.partners.toLocaleString()} partners</span>
                                                                <span>{s.detail.bom.payout}</span>
                                                                <code>{s.detail.bom.calc}</code>
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* Fraud signals list for S6 */}
                                                    {s.detail.signals && (
                                                        <ul className="stress-detail__signals">
                                                            {s.detail.signals.map((sig, i) => (
                                                                <li key={i}>{sig}</li>
                                                            ))}
                                                        </ul>
                                                    )}

                                                    <p className="stress-detail__note">{s.detail.note}</p>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {/* Payout bar chart */}
            <div className="stress-chart">
                <p className="stress-chart__label">Estimated payout exposure per scenario</p>
                <div className="stress-chart__bars">
                    {SCENARIOS.map(s => {
                        const maxPayout = 10800000;
                        const pct = s.payoutRaw === 0 ? 2 : Math.round((s.payoutRaw / maxPayout) * 100);
                        const badge = BADGE_STYLES[s.badge];
                        return (
                            <div key={s.id} className="stress-chart__bar-row">
                                <span className="stress-chart__bar-id">{s.id}</span>
                                <div className="stress-chart__bar-track">
                                    <div
                                        className="stress-chart__bar-fill"
                                        style={{ width: `${pct}%`, background: badge.color }}
                                    />
                                </div>
                                <span className="stress-chart__bar-value">{s.payout}</span>
                            </div>
                        );
                    })}
                </div>
            </div>
        </section>
    );
}