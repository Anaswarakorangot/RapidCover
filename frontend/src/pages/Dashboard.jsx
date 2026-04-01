import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardBody, CoverageCard, ClaimList } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const TRIGGER_LABELS = {
  rain: { icon: '🌧️', label: 'Heavy Rain', color: 'bg-blue-50 border-blue-200 text-blue-700' },
  heat: { icon: '🌡️', label: 'Extreme Heat', color: 'bg-red-50 border-red-200 text-red-700' },
  aqi: { icon: '💨', label: 'Dangerous AQI', color: 'bg-yellow-50 border-yellow-200 text-yellow-700' },
  shutdown: { icon: '🚫', label: 'Civic Shutdown', color: 'bg-purple-50 border-purple-200 text-purple-700' },
  closure: { icon: '🏪', label: 'Store Closure', color: 'bg-gray-50 border-gray-200 text-gray-700' },
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
              const info = TRIGGER_LABELS[trigger.trigger_type] || { icon: '⚠️', label: trigger.trigger_type, color: 'bg-gray-50 text-gray-700 border-gray-200' };
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
      <CoverageCard policy={policy} />

      {/* Earnings Summary */}
      <div>
        <h2 className="font-semibold text-gray-900 mb-3">Earnings</h2>
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
      </div>

      {/* Recent Claims */}
      {recentClaims.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Recent Claims</h2>
            <Link to="/claims" className="text-blue-600 text-sm font-medium">
              View All →
            </Link>
          </div>
          <ClaimList claims={recentClaims} maxItems={3} />
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