/**
 * CoverageCard — Modular policy coverage display component.
 * Used on Dashboard and Policy pages.
 */
import { Link } from 'react-router-dom';
import { Card, CardBody } from './Card';
import { Button } from './Button';

const TIER_GRADIENT = {
    basic: 'from-slate-600 to-slate-700',
    standard: 'from-blue-600 to-blue-700',
    premium: 'from-violet-600 to-violet-700',
};

export function CoverageCard({ policy, compact = false }) {
    if (!policy) {
        return (
            <Card>
                <CardBody className="text-center py-8">
                    <span className="text-4xl">🛡️</span>
                    <h3 className="font-semibold text-gray-900 mt-3">No Active Policy</h3>
                    <p className="text-gray-600 text-sm mt-1">Protect your income from disruptions</p>
                    <Link to="/policy"><Button className="mt-4">Get Coverage</Button></Link>
                </CardBody>
            </Card>
        );
    }

    const gradient = TIER_GRADIENT[policy.tier] || TIER_GRADIENT.standard;
    const daysLeft = Math.ceil((new Date(policy.expires_at) - new Date()) / (1000 * 60 * 60 * 24));

    if (compact) {
        return (
            <div className={`rounded-xl bg-gradient-to-br ${gradient} text-white p-4 flex items-center justify-between`}>
                <div>
                    <p className="text-white/70 text-xs">Active Policy</p>
                    <p className="font-bold capitalize">{policy.tier}</p>
                </div>
                <div className="text-right">
                    <p className="text-white/70 text-xs">Daily Payout</p>
                    <p className="font-bold">₹{policy.max_daily_payout}</p>
                </div>
                <span className="bg-green-400 text-green-900 text-xs font-semibold px-2 py-1 rounded-full ml-2">Active</span>
            </div>
        );
    }

    return (
        <Card className={`bg-gradient-to-br ${gradient} text-white border-0`}>
            <CardBody>
                <div className="flex justify-between items-start">
                    <div>
                        <p className="text-white/70 text-sm">Active Policy</p>
                        <p className="text-2xl font-bold mt-1 capitalize">{policy.tier}</p>
                    </div>
                    <span className="bg-green-400 text-green-900 text-xs font-semibold px-2 py-1 rounded-full">Active</span>
                </div>
                <div className="mt-4 grid grid-cols-3 gap-3">
                    <div>
                        <p className="text-white/70 text-xs">Daily Payout</p>
                        <p className="text-lg font-semibold">₹{policy.max_daily_payout}</p>
                    </div>
                    <div>
                        <p className="text-white/70 text-xs">Max Days/Week</p>
                        <p className="text-lg font-semibold">{policy.max_days_per_week}</p>
                    </div>
                    <div>
                        <p className="text-white/70 text-xs">Days Left</p>
                        <p className="text-lg font-semibold">{daysLeft > 0 ? daysLeft : '—'}</p>
                    </div>
                </div>
                <div className="mt-3 flex items-center justify-between">
                    <p className="text-sm text-white/70">
                        Expires: {new Date(policy.expires_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                    </p>
                    <Link to="/policy">
                        <button className="text-xs bg-white/20 hover:bg-white/30 text-white px-3 py-1 rounded-full transition-colors">
                            Details
                        </button>
                    </Link>
                </div>
            </CardBody>
        </Card>
    );
}