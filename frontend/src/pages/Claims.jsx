import { useState, useEffect } from 'react';
import { Card, CardBody } from '../components/ui';
import api from '../services/api';

const STATUS_STYLES = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-blue-100 text-blue-800',
  paid: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
};

const TRIGGER_ICONS = {
  rain: '🌧️',
  heat: '🌡️',
  aqi: '💨',
  shutdown: '🚫',
  closure: '🏪',
};

const TRIGGER_LABELS = {
  rain: 'Heavy Rain',
  heat: 'Extreme Heat',
  aqi: 'Dangerous AQI',
  shutdown: 'Civic Shutdown',
  closure: 'Store Closure',
};

export function Claims() {
  const [claims, setClaims] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [claimsData, summaryData] = await Promise.all([
          api.getClaims(),
          api.getClaimsSummary(),
        ]);
        setClaims(claimsData.claims);
        setSummary(summaryData);
      } catch (error) {
        console.error('Failed to load claims:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Claims</h1>
        <p className="text-gray-600">Your automatic payouts</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardBody className="text-center">
            <p className="text-gray-600 text-sm">Total Received</p>
            <p className="text-2xl font-bold text-green-600">
              ₹{summary?.total_paid || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {summary?.total_claims || 0} claims
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="text-center">
            <p className="text-gray-600 text-sm">Pending</p>
            <p className="text-2xl font-bold text-orange-500">
              ₹{summary?.pending_amount || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {summary?.pending_claims || 0} claims
            </p>
          </CardBody>
        </Card>
      </div>

      {/* Claims List */}
      <div>
        <h2 className="font-semibold text-gray-900 mb-3">Recent Claims</h2>
        {claims.length === 0 ? (
          <Card>
            <CardBody className="text-center py-8">
              <span className="text-4xl">📭</span>
              <h3 className="font-semibold text-gray-900 mt-3">No Claims Yet</h3>
              <p className="text-gray-600 text-sm mt-1">
                Claims are automatically created when disruption events occur
              </p>
            </CardBody>
          </Card>
        ) : (
          <div className="space-y-3">
            {claims.map((claim) => (
              <Card key={claim.id}>
                <CardBody>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">
                        {TRIGGER_ICONS[claim.trigger_type] || '📋'}
                      </span>
                      <div>
                        <p className="font-semibold text-gray-900">
                          {TRIGGER_LABELS[claim.trigger_type] || claim.trigger_type}
                        </p>
                        <p className="text-sm text-gray-500">
                          {new Date(claim.created_at).toLocaleDateString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-gray-900">₹{claim.amount}</p>
                      <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[claim.status]}`}>
                        {claim.status}
                      </span>
                    </div>
                  </div>
                  {claim.paid_at && (
                    <p className="text-xs text-gray-500 mt-2">
                      Paid on {new Date(claim.paid_at).toLocaleDateString()}
                      {claim.upi_ref && ` • Ref: ${claim.upi_ref}`}
                    </p>
                  )}
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Info */}
      <Card className="bg-blue-50 border-blue-200">
        <CardBody className="text-sm text-blue-800">
          <p className="font-semibold mb-1">💡 How payouts work</p>
          <p>
            When we detect a covered event in your zone, we automatically process your claim.
            Money is sent directly to your UPI - no forms needed!
          </p>
        </CardBody>
      </Card>
    </div>
  );
}
