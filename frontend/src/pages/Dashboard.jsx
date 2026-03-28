import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardBody, Button } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export function Dashboard() {
  const { user } = useAuth();
  const [policy, setPolicy] = useState(null);
  const [summary, setSummary] = useState(null);
  const [zone, setZone] = useState(null);
  const [triggers, setTriggers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [policyData, summaryData] = await Promise.all([
          api.getActivePolicy().catch(() => null),
          api.getClaimsSummary(),
        ]);
        setPolicy(policyData);
        setSummary(summaryData);

        // Load zone info if user has zone_id
        if (user?.zone_id) {
          const zoneData = await api.getZone(user.zone_id).catch(() => null);
          setZone(zoneData);

          // Load active triggers for this zone
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

  const TRIGGER_LABELS = {
    rain: { icon: '🌧️', label: 'Heavy Rain', color: 'blue' },
    heat: { icon: '🌡️', label: 'Extreme Heat', color: 'red' },
    aqi: { icon: '💨', label: 'Dangerous AQI', color: 'yellow' },
    shutdown: { icon: '🚫', label: 'Civic Shutdown', color: 'purple' },
    closure: { icon: '🏪', label: 'Store Closure', color: 'gray' },
  };

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Hello, {user?.name?.split(' ')[0]} 👋
        </h1>
        <p className="text-gray-600">
          {policy ? 'Your coverage is active' : 'Get protected today'}
        </p>
        {zone && (
          <p className="text-sm text-gray-500 mt-1">
            Zone: {zone.name} ({zone.code})
          </p>
        )}
      </div>

      {/* Active Triggers Alert */}
      {triggers.length > 0 && (
        <Card className="bg-red-50 border-red-200">
          <CardBody>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-red-600 font-semibold">Active Disruptions</span>
              <span className="bg-red-600 text-white text-xs px-2 py-0.5 rounded-full">
                {triggers.length}
              </span>
            </div>
            <div className="space-y-2">
              {triggers.map((trigger) => {
                const info = TRIGGER_LABELS[trigger.trigger_type] || { icon: '⚠️', label: trigger.trigger_type };
                return (
                  <div key={trigger.id} className="flex items-center gap-2 text-sm text-red-700">
                    <span>{info.icon}</span>
                    <span className="font-medium">{info.label}</span>
                    <span className="text-red-500">- Severity {trigger.severity}/5</span>
                  </div>
                );
              })}
            </div>
            {policy && (
              <p className="text-xs text-red-600 mt-2">
                You're covered! Claims will be auto-processed.
              </p>
            )}
          </CardBody>
        </Card>
      )}

      {/* Active Policy Card */}
      {policy ? (
        <Card className="bg-gradient-to-br from-blue-600 to-blue-700 text-white border-0">
          <CardBody>
            <div className="flex justify-between items-start">
              <div>
                <p className="text-blue-100 text-sm">Active Policy</p>
                <p className="text-2xl font-bold mt-1 capitalize">{policy.tier}</p>
              </div>
              <span className="bg-green-400 text-green-900 text-xs font-semibold px-2 py-1 rounded-full">
                Active
              </span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <p className="text-blue-100 text-xs">Daily Payout</p>
                <p className="text-lg font-semibold">₹{policy.max_daily_payout}</p>
              </div>
              <div>
                <p className="text-blue-100 text-xs">Max Days/Week</p>
                <p className="text-lg font-semibold">{policy.max_days_per_week}</p>
              </div>
            </div>
            <div className="mt-4 text-sm text-blue-100">
              Expires: {new Date(policy.expires_at).toLocaleDateString()}
            </div>
          </CardBody>
        </Card>
      ) : (
        <Card>
          <CardBody className="text-center py-8">
            <span className="text-4xl">🛡️</span>
            <h3 className="font-semibold text-gray-900 mt-3">No Active Policy</h3>
            <p className="text-gray-600 text-sm mt-1">
              Protect your income from disruptions
            </p>
            <Link to="/policy">
              <Button className="mt-4">Get Coverage</Button>
            </Link>
          </CardBody>
        </Card>
      )}

      {/* Claims Summary */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardBody className="text-center">
            <p className="text-gray-600 text-sm">Total Received</p>
            <p className="text-2xl font-bold text-green-600">
              ₹{summary?.total_paid || 0}
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="text-center">
            <p className="text-gray-600 text-sm">Pending</p>
            <p className="text-2xl font-bold text-orange-500">
              ₹{summary?.pending_amount || 0}
            </p>
          </CardBody>
        </Card>
      </div>

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
            {[
              { icon: '🌧️', label: 'Heavy Rain & Floods' },
              { icon: '🌡️', label: 'Extreme Heat (>43°C)' },
              { icon: '💨', label: 'Dangerous AQI (>400)' },
              { icon: '🚫', label: 'Curfew & Bandh' },
              { icon: '🏪', label: 'Dark Store Closures' },
            ].map((item) => (
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
