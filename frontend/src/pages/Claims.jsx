import { useState, useEffect } from 'react';
import { Card, CardBody, ClaimList } from '../components/ui';
import api from '../services/api';

const STATUS_FILTERS = ['all', 'paid', 'pending', 'approved', 'rejected'];

export function Claims() {
  const [claims, setClaims] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Claims</h1>
        <p className="text-gray-500 text-sm">Your automatic payouts</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardBody className="text-center">
            <p className="text-gray-500 text-xs mb-1">Total Received</p>
            <p className="text-2xl font-bold text-green-600">
              ₹{summary?.total_paid || 0}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {summary?.total_claims || 0} claims
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="text-center">
            <p className="text-gray-500 text-xs mb-1">Pending</p>
            <p className="text-2xl font-bold text-orange-500">
              ₹{summary?.pending_amount || 0}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {summary?.pending_claims || 0} claims
            </p>
          </CardBody>
        </Card>
      </div>

      {/* Status Filter */}
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => { setStatusFilter(f); setPage(1); }}
            className={`flex-shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors capitalize ${statusFilter === f
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
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
          {total > 0 && (
            <span className="text-xs text-gray-400">{total} total</span>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
          </div>
        ) : (
          <ClaimList claims={claims} />
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 mt-4">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 text-sm bg-gray-100 rounded-lg disabled:opacity-40 hover:bg-gray-200"
            >
              ← Prev
            </button>
            <span className="text-sm text-gray-600">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 text-sm bg-gray-100 rounded-lg disabled:opacity-40 hover:bg-gray-200"
            >
              Next →
            </button>
          </div>
        )}
      </div>

      {/* Info Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardBody className="text-sm text-blue-800">
          <p className="font-semibold mb-1">💡 How payouts work</p>
          <p>
            When we detect a covered event in your zone, we automatically process your claim.
            Money is sent directly to your UPI — no forms needed!
          </p>
        </CardBody>
      </Card>
    </div>
  );
}