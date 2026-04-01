import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardBody, Button } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const TRIGGER_INFO = {
  rain: { icon: '🌧️', label: 'Heavy Rain', color: 'bg-blue-50 border-blue-200 text-blue-700' },
  heat: { icon: '🌡️', label: 'Extreme Heat', color: 'bg-red-50 border-red-200 text-red-700' },
  aqi: { icon: '💨', label: 'Dangerous AQI', color: 'bg-yellow-50 border-yellow-200 text-yellow-700' },
  shutdown: { icon: '🚫', label: 'Civic Shutdown', color: 'bg-purple-50 border-purple-200 text-purple-700' },
  closure: { icon: '🏪', label: 'Store Closure', color: 'bg-gray-50 border-gray-200 text-gray-700' },
};

const TIER_GRADIENT = {
  basic: 'from-slate-600 to-slate-700',
  standard: 'from-blue-600 to-blue-700',
  premium: 'from-violet-600 to-violet-700',
};

const COVERAGE_EVENTS = [
  { icon: '🌧️', label: 'Heavy Rain & Floods' },
  { icon: '🌡️', label: 'Extreme Heat (>43°C)' },
  { icon: '💨', label: 'Dangerous AQI (>400)' },
  { icon: '🚫', label: 'Curfew & Bandh' },
  { icon: '🏪', label: 'Dark Store Closures' },
];

export function Dashboard() {
  const { user } = useAuth();
  const [policy, setPolicy] = useState(null);
  const [summary, setSummary] = useState(null);
  const [zone, setZone] = useState(null);
  const [triggers, setTriggers] = useState([]);
  const [recentClaims, setRecentClaims] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [policyData, summaryData, claimsData] = await Promise.all([
          api.getActivePolicy().catch(() => null),
          api.getClaimsSummary(),
          api.getClaims(1, 3).catch(() => ({ claims: [] })),
        ]);
        setPolicy(policyData);
        setSummary(summaryData);
        setRecentClaims(claimsData.claims || []);

        if (user?.zone_id) {
          const zoneData = await api.getZone(user.zone_id).catch(() => null);
          setZone(zoneData);
          const triggerData = await api.getActiveTriggers(user.zone_id).catch(() => ({ triggers: [] }));
          setTriggers(triggerData.triggers || []);
        }
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [user?.zone_id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const tierGradient = TIER_GRADIENT[policy?.tier] || TIER_GRADIENT.standard;
  const daysLeft = policy
    ? Math.ceil((new Date(policy.expires_at) - new Date()) / (1000 * 60 * 60 * 24))
    : 0;

  return (
    <div className="space-y-6">

      {/* Welcome Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Hello, {user?.name?.split(' ')[0]} 👋
          </h1>
          <p className="text-gray-500 text-sm mt-0.5">
            {zone ? `${zone.name} (${zone.code})` : 'Set your zone in profile'}
          </p>
        </div>
        {policy && (
          <span className="flex items-center gap-1.5 bg-green-50 border border-green-200 text-green-700 text-xs font-semibold px-3 py-1.5 rounded-full">
            <span className="h-1.5 w-1.5 bg-green-500 rounded-full animate-pulse" />
            Covered
          </span>
        )}
      </div>

      {/* Active Disruptions Alert */}
      {triggers.length > 0 && (
        <div className="rounded-xl border-2 border-red-200 bg-red-50 p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-red-600 font-semibold text-sm">⚠️ Active Disruptions in Your Zone</span>
            <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full font-bold">
              {triggers.length}
            </span>
          </div>
          <div className="space-y-2">
            {triggers.map((trigger) => {
              const info = TRIGGER_INFO[trigger.trigger_type] || { icon: '⚠️', label: trigger.trigger_type, color: 'bg-gray-50 border-gray-200 text-gray-700' };
              return (
                <div key={trigger.id} className={`flex items-center justify-between px-3 py-2 rounded-lg border text-sm ${info.color}`}>
                  <div className="flex items-center gap-2">
                    <span>{info.icon}</span>
                    <span className="font-medium">{info.label}</span>
                  </div>
                  <span className="text-xs font-semibold">Severity {trigger.severity}/5</span>
                </div>
              );
            })}
          </div>
          {policy && (
            <p className="text-xs text-red-600 mt-3 font-medium">
              ✅ You're covered! Claims will be auto-processed.
            </p>
          )}
        </div>
      )}

      {/* Coverage Card */}
      {policy ? (
        <Card className={`bg-gradient-to-br ${tierGradient} text-white border-0`}>
          <CardBody>
            <div className="flex justify-between items-start">
              <div>
                <p className="text-white/70 text-sm">Active Policy</p>
                <p className="text-2xl font-bold mt-1 capitalize">{policy.tier}</p>
              </div>
              <span className="bg-green-400 text-green-900 text-xs font-semibold px-2 py-1 rounded-full">
                Active
              </span>
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
      ) : (
        <Card>
          <CardBody className="text-center py-8">
            <span className="text-4xl">🛡️</span>
            <h3 className="font-semibold text-gray-900 mt-3">No Active Policy</h3>
            <p className="text-gray-600 text-sm mt-1">Protect your income from disruptions</p>
            <Link to="/policy">
              <Button className="mt-4">Get Coverage</Button>
            </Link>
          </CardBody>
        </Card>
      )}

      {/* Earnings Summary */}
      <div>
        <h2 className="font-semibold text-gray-900 mb-3">Earnings</h2>
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
      </div>

      {/* Recent Claims */}
      {recentClaims.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Recent Claims</h2>
            <Link to="/claims" className="text-blue-600 text-sm font-medium">View All →</Link>
          </div>
          <div className="space-y-3">
            {recentClaims.map((claim) => {
              const info = TRIGGER_INFO[claim.trigger_type] || { icon: '📋', label: claim.trigger_type };
              const statusColors = { pending: 'text-yellow-600 bg-yellow-50', approved: 'text-blue-600 bg-blue-50', paid: 'text-green-600 bg-green-50', rejected: 'text-red-600 bg-red-50' };
              return (
                <Card key={claim.id}>
                  <CardBody>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{info.icon}</span>
                        <div>
                          <p className="font-medium text-gray-900 text-sm">{info.label}</p>
                          <p className="text-xs text-gray-500">
                            {new Date(claim.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-gray-900">₹{claim.amount}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[claim.status] || 'text-gray-600 bg-gray-50'}`}>
                          {claim.status}
                        </span>
                      </div>
                    </div>
                  </CardBody>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div>
        <h2 className="font-semibold text-gray-900 mb-3">Quick Actions</h2>
        <div className="grid grid-cols-2 gap-3">
          <Link to="/policy">
            <Card className="hover:shadow-md transition-shadow">
              <CardBody className="text-center py-4">
                <span className="text-2xl">📋</span>
                <p className="text-sm font-medium text-gray-700 mt-2">View Policy</p>
              </CardBody>
            </Card>
          </Link>
          <Link to="/claims">
            <Card className="hover:shadow-md transition-shadow">
              <CardBody className="text-center py-4">
                <span className="text-2xl">💰</span>
                <p className="text-sm font-medium text-gray-700 mt-2">Claim History</p>
              </CardBody>
            </Card>
          </Link>
        </div>
      </div>

      {/* Coverage Info */}
      <Card>
        <CardBody>
          <h3 className="font-semibold text-gray-900 mb-3">You're covered for:</h3>
          <div className="space-y-2 text-sm">
            {COVERAGE_EVENTS.map((item) => (
              <div key={item.label} className="flex items-center gap-2 text-gray-700">
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>

    </div>
  );
}