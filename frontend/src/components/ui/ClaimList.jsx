/**
 * ClaimList — Reusable claim list with tap-to-view detail sheet.
 */
import { useState } from 'react';
import { Card, CardBody } from './Card';
import { TRIGGER_ICONS, TRIGGER_LABELS } from './ClaimConstants';

const STATUS_STYLES = {
    pending: 'bg-yellow-100 text-yellow-800 border border-yellow-200',
    approved: 'bg-blue-100 text-blue-800 border border-blue-200',
    paid: 'bg-green-100 text-green-800 border border-green-200',
    rejected: 'bg-red-100 text-red-800 border border-red-200',
};
const STATUS_ICONS = { pending: '⏳', approved: '✅', paid: '💸', rejected: '❌' };

function ClaimDetail({ claim, onClose }) {
    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-center p-4" onClick={onClose}>
            <div className="bg-white rounded-2xl w-full max-w-lg p-6 space-y-4" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <span className="text-3xl">{TRIGGER_ICONS[claim.trigger_type] || '📋'}</span>
                        <div>
                            <h3 className="font-bold text-gray-900">{TRIGGER_LABELS[claim.trigger_type] || claim.trigger_type}</h3>
                            <p className="text-sm text-gray-500">Claim #{claim.id}</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">✕</button>
                </div>

                <div className="bg-gray-50 rounded-xl p-4 grid grid-cols-2 gap-4">
                    <div>
                        <p className="text-xs text-gray-500">Payout Amount</p>
                        <p className="text-2xl font-bold text-gray-900">₹{claim.amount}</p>
                    </div>
                    <div>
                        <p className="text-xs text-gray-500">Status</p>
                        <span className={`inline-flex items-center gap-1 mt-1 px-3 py-1 rounded-full text-sm font-medium ${STATUS_STYLES[claim.status]}`}>
                            {STATUS_ICONS[claim.status]} {claim.status}
                        </span>
                    </div>
                    <div>
                        <p className="text-xs text-gray-500">Filed On</p>
                        <p className="text-sm font-medium text-gray-800">
                            {new Date(claim.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-gray-500">Time</p>
                        <p className="text-sm font-medium text-gray-800">
                            {new Date(claim.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                        </p>
                    </div>
                </div>

                {claim.status === 'paid' && (
                    <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-2">
                        <p className="text-xs font-semibold text-green-700 uppercase tracking-wide">Payment Details</p>
                        {claim.paid_at && (
                            <div className="flex justify-between text-sm">
                                <span className="text-green-700">Paid On</span>
                                <span className="font-medium text-green-900">
                                    {new Date(claim.paid_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                                </span>
                            </div>
                        )}
                        {claim.upi_ref && (
                            <div className="flex justify-between text-sm">
                                <span className="text-green-700">UPI Ref</span>
                                <span className="font-mono font-medium text-green-900 text-xs">{claim.upi_ref}</span>
                            </div>
                        )}
                    </div>
                )}

                {claim.trigger_started_at && (
                    <p className="text-sm text-gray-500">
                        <span className="text-gray-400">Event started: </span>
                        {new Date(claim.trigger_started_at).toLocaleString('en-IN')}
                    </p>
                )}

                <button onClick={onClose} className="w-full bg-gray-900 text-white py-3 rounded-xl font-medium hover:bg-gray-800 transition-colors">
                    Close
                </button>
            </div>
        </div>
    );
}

export function ClaimList({ claims = [], maxItems = null }) {
    const [selected, setSelected] = useState(null);
    const displayed = maxItems ? claims.slice(0, maxItems) : claims;

    if (claims.length === 0) {
        return (
            <Card>
                <CardBody className="text-center py-8">
                    <span className="text-4xl">📭</span>
                    <h3 className="font-semibold text-gray-900 mt-3">No Claims Yet</h3>
                    <p className="text-gray-600 text-sm mt-1">Claims are automatically created when disruption events occur</p>
                </CardBody>
            </Card>
        );
    }

    return (
        <>
            {selected && <ClaimDetail claim={selected} onClose={() => setSelected(null)} />}
            <div className="space-y-3">
                {displayed.map((claim) => (
                    <button key={claim.id} className="w-full text-left" onClick={() => setSelected(claim)}>
                        <Card className="hover:shadow-md transition-shadow active:scale-[0.99] cursor-pointer">
                            <CardBody>
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <span className="text-2xl">{TRIGGER_ICONS[claim.trigger_type] || '📋'}</span>
                                        <div>
                                            <p className="font-semibold text-gray-900 text-sm">
                                                {TRIGGER_LABELS[claim.trigger_type] || claim.trigger_type}
                                            </p>
                                            <p className="text-xs text-gray-500">
                                                {new Date(claim.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="text-right flex flex-col items-end gap-1">
                                        <p className="font-bold text-gray-900">₹{claim.amount}</p>
                                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[claim.status]}`}>
                                            {STATUS_ICONS[claim.status]} {claim.status}
                                        </span>
                                    </div>
                                </div>
                                {claim.status === 'paid' && claim.upi_ref && (
                                    <p className="text-xs text-gray-400 mt-2 font-mono">Ref: {claim.upi_ref}</p>
                                )}
                            </CardBody>
                        </Card>
                    </button>
                ))}
            </div>
        </>
    );
}
