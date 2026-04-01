import { useState, useEffect } from 'react';
import { Card, CardBody } from '../components/ui';
import api from '../services/api';

const STATUS_STYLES = {
  pending: 'bg-yellow-100 text-yellow-800 border border-yellow-200',
  approved: 'bg-blue-100 text-blue-800 border border-blue-200',
  paid: 'bg-green-100 text-green-800 border border-green-200',
  rejected: 'bg-red-100 text-red-800 border border-red-200',
};

const STATUS_ICONS = { pending: '⏳', approved: '✅', paid: '💸', rejected: '❌' };

const TRIGGER_ICONS = { rain: '🌧️', heat: '🌡️', aqi: '💨', shutdown: '🚫', closure: '🏪' };
const TRIGGER_LABELS = { rain: 'Heavy Rain', heat: 'Extreme Heat', aqi: 'Dangerous AQI', shutdown: 'Civic Shutdown', closure: 'Store Closure' };

const STATUS_FILTERS = ['all', 'paid', 'pending', 'approved', 'rejected'];

function ClaimDetailSheet({ claim, onClose }) {
  if (!claim) return null;
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

export function Claims() {
  const [claims, setClaims] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [selectedClaim, setSelectedClaim] = useState(null);
  const PAGE_SIZE = 10;

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const filter = statusFilter === 'all' ? undefined : statusFilter;
        const [claimsData, summaryData] = await Promise.all([
          api.getClaims(page, PAGE_SIZE, filter),
          api.getClaimsSummary(),
        ]);
        setClaims(claimsData.claims);
        setTotal(claimsData.total);
        setSummary(summaryData);
      } catch (error) {
        console.error('Failed to load claims:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [page, statusFilter]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-6">
      <ClaimDetailSheet claim={selectedClaim} onClose={() => setSelectedClaim(null)} />

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Claims</h1>
        <p className="text-gray-500 text-sm">Your automatic payouts</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardBody className="text-center">
            <p className="text-gray-500 text-xs mb-1">Total Received</p>
            <p className="text-2xl font-bold text-green-600">₹{summary?.total_paid || 0}</p>
            <p className="text-xs text-gray-400 mt-1">{summary?.total_claims || 0} claims</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="text-center">
            <p className="text-gray-500 text-xs mb-1">Pending</p>
            <p className="text-2xl font-bold text-orange-500">₹{summary?.pending_amount || 0}</p>
            <p className="text-xs text-gray-400 mt-1">{summary?.pending_claims || 0} claims</p>
          </CardBody>
        </Card>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => { setStatusFilter(f); setPage(1); }}
            className={`flex-shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors capitalize ${statusFilter === f ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Claims List */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-900">
            {statusFilter === 'all' ? 'All Claims' : `${statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)} Claims`}
          </h2>
          {total > 0 && <span className="text-xs text-gray-400">{total} total</span>}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
          </div>
        ) : claims.length === 0 ? (
          <Card>
            <CardBody className="text-center py-8">
              <span className="text-4xl">📭</span>
              <h3 className="font-semibold text-gray-900 mt-3">No Claims Yet</h3>
              <p className="text-gray-600 text-sm mt-1">Claims are automatically created when disruption events occur</p>
            </CardBody>
          </Card>
        ) : (
          <div className="space-y-3">
            {claims.map((claim) => (
              <button key={claim.id} className="w-full text-left" onClick={() => setSelectedClaim(claim)}>
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
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 mt-4">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="px-3 py-1.5 text-sm bg-gray-100 rounded-lg disabled:opacity-40 hover:bg-gray-200">
              ← Prev
            </button>
            <span className="text-sm text-gray-600">{page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="px-3 py-1.5 text-sm bg-gray-100 rounded-lg disabled:opacity-40 hover:bg-gray-200">
              Next →
            </button>
          </div>
        )}
      </div>

      {/* Info */}
      <Card className="bg-blue-50 border-blue-200">
        <CardBody className="text-sm text-blue-800">
          <p className="font-semibold mb-1">💡 How payouts work</p>
          <p>When we detect a covered event in your zone, we automatically process your claim. Money is sent directly to your UPI — no forms needed!</p>
        </CardBody>
      </Card>
    </div>
  );
}