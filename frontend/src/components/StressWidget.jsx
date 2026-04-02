import React, { useState } from 'react';

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
        payoutRaw: 9000000,
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
        poolPct: '8%',
        mode: 'Auto-reject + Fraud queue. Expected: 35–40 accounts auto-rejected (score >0.90), 10–15 to manual queue (0.75–0.90).',
        badge: 'fraud',
        detail: {
            signals: [
                'device_fingerprint_match (w5)',
                'centroid_drift_score (w7)',
                'claim_frequency_score (w4)',
                'gps_coherence (w1)',
            ],
            note: 'Admin fraud queue shows cluster pattern — all 50 claims from same event, same zone, same device profile. Bulk-reject available.',
        },
    },
];

const BADGE_STYLES = {
    reinsurance: { bg: '#fee2e2', color: 'var(--error)', label: 'Reinsurance' },
    catastrophic: { bg: '#fef2f2', color: 'var(--error)', label: 'Catastrophic' },
    proportional: { bg: '#fef9c3', color: 'var(--warning)', label: 'Proportional' },
    normal: { bg: 'var(--green-light)', color: 'var(--green-primary)', label: 'Normal' },
    fraud: { bg: '#f3e8ff', color: '#9333ea', label: 'Fraud Blocked' },
};

export default function StressWidget() {
    const [expanded, setExpanded] = useState(null);

    function toggle(id) {
        setExpanded(prev => (prev === id ? null : id));
    }

    return (
        <section className="stress-widget">
            <div className="stress-widget__header" style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h2 className="stress-widget__title" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)' }}>⚡ Stress Scenarios</h2>
                    <p className="stress-widget__subtitle" style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.4rem' }}>
                        Actuarial stress test — 6 scenarios modelling extreme but plausible events
                    </p>
                </div>
                <span className="stress-widget__count" style={{ fontSize: '0.75rem', fontWeight: 800, background: 'var(--gray-bg)', padding: '0.4rem 0.8rem', borderRadius: '10px', color: 'var(--text-mid)' }}>{SCENARIOS.length} scenarios</span>
            </div>

            <div className="stress-table-wrapper" style={{ background: 'var(--white)', borderRadius: '24px', border: '1.5px solid var(--border)', overflow: 'hidden' }}>
                <table className="stress-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead style={{ background: 'var(--gray-bg)', borderBottom: '1.5px solid var(--border)' }}>
                        <tr style={{ textAlign: 'left' }}>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>ID</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Scenario</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Cities</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)', textAlign: 'right' }}>Partners</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)', textAlign: 'right' }}>Est. Payout</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)', textAlign: 'center' }}>Weekly Pool</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>System Mode</th>
                            <th style={{ padding: '1rem' }}></th>
                        </tr>
                    </thead>
                    <tbody>
                        {SCENARIOS.map(s => {
                            const badge = BADGE_STYLES[s.badge];
                            const isOpen = expanded === s.id;
                            return (
                                <React.Fragment key={s.id}>
                                    <tr 
                                        style={{ borderBottom: '1px solid var(--border)', background: isOpen ? 'var(--gray-bg)' : 'transparent', transition: 'all 0.15s' }}
                                    >
                                        <td style={{ padding: '1rem' }}><code style={{ fontWeight: 800 }}>{s.id}</code></td>
                                        <td style={{ padding: '1rem', fontWeight: 700, fontSize: '0.9rem' }}>{s.name}</td>
                                        <td style={{ padding: '1rem', fontSize: '0.8rem', color: 'var(--text-mid)' }}>{s.cities}</td>
                                        <td style={{ padding: '1rem', textAlign: 'right', fontWeight: 700 }}>{s.partners.toLocaleString()}</td>
                                        <td style={{ padding: '1rem', textAlign: 'right', fontWeight: 900, color: 'var(--text-dark)' }}>{s.payout}</td>
                                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                                            <span 
                                                style={{ fontSize: '0.65rem', fontWeight: 900, padding: '0.3rem 0.6rem', borderRadius: '8px', background: badge.bg, color: badge.color, border: `1px solid ${badge.color}25` }}
                                            >
                                                {s.poolPct}
                                            </span>
                                        </td>
                                        <td style={{ padding: '1rem' }}>
                                            <span 
                                                style={{ fontSize: '0.65rem', fontWeight: 900, padding: '0.3rem 0.6rem', borderRadius: '8px', background: 'var(--gray-bg)', color: 'var(--text-mid)', textTransform: 'uppercase' }}
                                            >
                                                {badge.label}
                                            </span>
                                        </td>
                                        <td style={{ padding: '1rem' }}>
                                            <button 
                                                onClick={() => toggle(s.id)}
                                                style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.75rem', color: 'var(--text-light)', transition: 'transform 0.2s', transform: isOpen ? 'rotate(180deg)' : 'none' }}
                                            >
                                                ▼
                                            </button>
                                        </td>
                                    </tr>
                                    {isOpen && (
                                        <tr style={{ background: 'var(--gray-bg)' }}>
                                            <td colSpan={8} style={{ padding: '0 1rem 1.5rem' }}>
                                                <div style={{ background: 'var(--white)', border: '1.5px solid var(--border)', borderRadius: '18px', padding: '1.25rem' }}>
                                                    <p style={{ fontSize: '0.85rem', color: 'var(--text-dark)', lineHeight: 1.6, marginBottom: '1rem' }}>
                                                        <strong style={{ fontFamily: 'Nunito', color: 'var(--green-primary)' }}>System Response:</strong> {s.mode}
                                                    </p>

                                                    {s.detail.blr && (
                                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                                                            <div style={{ background: 'var(--gray-bg)', padding: '0.75rem', borderRadius: '12px' }}>
                                                                <span style={{ fontSize: '0.7rem', fontWeight: 900, color: 'var(--text-light)', textTransform: 'uppercase', display: 'block', marginBottom: '0.2rem' }}>Bangalore</span>
                                                                <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>{s.detail.blr.payout}</span>
                                                                <code style={{ fontSize: '0.6rem', display: 'block', marginTop: '0.2rem', opacity: 0.7 }}>{s.detail.blr.calc}</code>
                                                            </div>
                                                            <div style={{ background: 'var(--gray-bg)', padding: '0.75rem', borderRadius: '12px' }}>
                                                                <span style={{ fontSize: '0.7rem', fontWeight: 900, color: 'var(--text-light)', textTransform: 'uppercase', display: 'block', marginBottom: '0.2rem' }}>Mumbai</span>
                                                                <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>{s.detail.bom.payout}</span>
                                                                <code style={{ fontSize: '0.6rem', display: 'block', marginTop: '0.2rem', opacity: 0.7 }}>{s.detail.bom.calc}</code>
                                                            </div>
                                                        </div>
                                                    )}

                                                    {s.detail.del && (
                                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                                                            <div style={{ background: 'var(--gray-bg)', padding: '0.75rem', borderRadius: '12px' }}>
                                                                <span style={{ fontSize: '0.7rem', fontWeight: 900, color: 'var(--text-light)', textTransform: 'uppercase', display: 'block', marginBottom: '0.2rem' }}>Delhi NCR</span>
                                                                <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>{s.detail.del.payout}</span>
                                                            </div>
                                                            <div style={{ background: 'var(--gray-bg)', padding: '0.75rem', borderRadius: '12px' }}>
                                                                <span style={{ fontSize: '0.7rem', fontWeight: 900, color: 'var(--text-light)', textTransform: 'uppercase', display: 'block', marginBottom: '0.2rem' }}>Satellite</span>
                                                                <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>{s.detail.noi.payout}</span>
                                                            </div>
                                                        </div>
                                                    )}

                                                    {s.detail.signals && (
                                                        <div style={{ marginBottom: '1rem' }}>
                                                            <span style={{ fontSize: '0.7rem', fontWeight: 900, color: 'var(--text-light)', textTransform: 'uppercase', display: 'block', marginBottom: '0.4rem' }}>Fraud Signals</span>
                                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                                                                {s.detail.signals.map((sig, i) => (
                                                                    <span key={i} style={{ fontSize: '0.65rem', background: 'var(--gray-bg)', padding: '0.2rem 0.5rem', borderRadius: '6px', color: 'var(--text-mid)', fontWeight: 600 }}>{sig}</span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}

                                                    <p style={{ fontSize: '0.75rem', color: 'var(--text-light)', padding: '0.75rem', background: 'var(--gray-bg)', borderRadius: '10px', marginTop: '0.5rem', borderLeft: '3px solid var(--border)' }}>
                                                        {s.detail.note}
                                                    </p>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            <div style={{ marginTop: '2.5rem', background: 'var(--white)', border: '1.5px solid var(--border)', borderRadius: '24px', padding: '1.5rem 2rem' }}>
                <p style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1rem', color: 'var(--text-dark)', marginBottom: '1.5rem' }}>Actuarial Payout Exposure</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {SCENARIOS.map(s => {
                        const maxPayout = 10800000;
                        const pct = s.payoutRaw === 0 ? 2 : Math.round((s.payoutRaw / maxPayout) * 100);
                        const badge = BADGE_STYLES[s.badge];
                        return (
                            <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <span style={{ width: 20, fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-light)' }}>{s.id}</span>
                                <div style={{ flex: 1, height: 10, background: 'var(--gray-bg)', borderRadius: '5px', overflow: 'hidden' }}>
                                    <div
                                        style={{ width: `${pct}%`, height: '100%', background: badge.color, borderRadius: '5px', transition: 'width 1s ease' }}
                                    />
                                </div>
                                <span style={{ width: 60, fontSize: '0.8rem', fontWeight: 900, color: 'var(--text-dark)', textAlign: 'right' }}>{s.payout}</span>
                            </div>
                        );
                    })}
                </div>
            </div>
        </section>
    );
}