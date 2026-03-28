import { useState, useEffect } from 'react';
import { Card, CardBody, Button } from '../components/ui';
import api from '../services/api';

const TRIGGER_TYPES = [
  { type: 'rain', label: 'Heavy Rain', icon: '🌧️' },
  { type: 'heat', label: 'Extreme Heat', icon: '🌡️' },
  { type: 'aqi', label: 'Dangerous AQI', icon: '💨' },
  { type: 'shutdown', label: 'Civic Shutdown', icon: '🚫' },
  { type: 'closure', label: 'Store Closure', icon: '🏪' },
];

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-blue-100 text-blue-800',
  rejected: 'bg-red-100 text-red-800',
  paid: 'bg-green-100 text-green-800',
};

export function Admin() {
  const [stats, setStats] = useState(null);
  const [zones, setZones] = useState([]);
  const [triggers, setTriggers] = useState([]);
  const [claims, setClaims] = useState([]);
  const [selectedZone, setSelectedZone] = useState('');
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [statsData, zonesData, triggersData, claimsData] = await Promise.all([
        api.getAdminDashboard(),
        api.getZones(),
        api.getAdminTriggers(true),
        api.getAdminClaims(),
      ]);
      setStats(statsData);
      setZones(zonesData);
      setTriggers(triggersData);
      setClaims(claimsData);
      if (zonesData.length > 0 && !selectedZone) {
        setSelectedZone(zonesData[0].id);
      }
    } catch (error) {
      console.error('Failed to load admin data:', error);
      setMessage('Failed to load data. Make sure to seed zones first.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSeedZones() {
    try {
      const result = await api.seedZones();
      setMessage(`Created ${result.zones_created} zones. Total: ${result.total_zones}`);
      loadData();
    } catch (error) {
      setMessage('Failed to seed zones: ' + error.message);
    }
  }

  async function simulateEvent(type) {
    if (!selectedZone) {
      setMessage('Please select a zone first');
      return;
    }

    setSimulating(true);
    setMessage('');

    try {
      let result;
      switch (type) {
        case 'rain':
          result = await api.simulateWeather(selectedZone, 60, null);
          break;
        case 'heat':
          result = await api.simulateWeather(selectedZone, null, 45);
          break;
        case 'aqi':
          result = await api.simulateAQI(selectedZone, 450);
          break;
        case 'shutdown':
          result = await api.simulateShutdown(selectedZone, 'Curfew imposed due to protests');
          break;
        case 'closure':
          result = await api.simulateClosure(selectedZone, 'Power outage at facility');
          break;
        default:
          return;
      }

      const triggerCount = result.triggers_created?.length || 0;
      setMessage(`Simulated ${type} event. Triggers created: ${triggerCount}`);
      loadData();
    } catch (error) {
      setMessage('Simulation failed: ' + error.message);
    } finally {
      setSimulating(false);
    }
  }

  async function handleProcessTrigger(triggerId) {
    try {
      const result = await api.processTrigger(triggerId);
      setMessage(`Created ${result.claims_created} claims from trigger`);
      loadData();
    } catch (error) {
      setMessage('Failed to process trigger: ' + error.message);
    }
  }

  async function handleClaimAction(claimId, action) {
    try {
      if (action === 'approve') {
        await api.approveClaim(claimId);
        setMessage('Claim approved');
      } else if (action === 'reject') {
        await api.rejectClaim(claimId, 'Manual rejection by admin');
        setMessage('Claim rejected');
      } else if (action === 'payout') {
        await api.payoutClaim(claimId);
        setMessage('Claim paid out');
      }
      loadData();
    } catch (error) {
      setMessage(`Failed to ${action} claim: ` + error.message);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <Button onClick={handleSeedZones} variant="secondary">
          Seed Zones
        </Button>
      </div>

      {message && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-2 rounded-lg text-sm">
          {message}
        </div>
      )}

      {/* Stats Grid */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardBody className="text-center py-3">
              <p className="text-2xl font-bold text-blue-600">{stats.total_partners}</p>
              <p className="text-xs text-gray-600">Partners</p>
            </CardBody>
          </Card>
          <Card>
            <CardBody className="text-center py-3">
              <p className="text-2xl font-bold text-green-600">{stats.active_policies}</p>
              <p className="text-xs text-gray-600">Active Policies</p>
            </CardBody>
          </Card>
          <Card>
            <CardBody className="text-center py-3">
              <p className="text-2xl font-bold text-red-600">{stats.active_triggers}</p>
              <p className="text-xs text-gray-600">Active Triggers</p>
            </CardBody>
          </Card>
          <Card>
            <CardBody className="text-center py-3">
              <p className="text-2xl font-bold text-yellow-600">{stats.pending_claims}</p>
              <p className="text-xs text-gray-600">Pending Claims</p>
            </CardBody>
          </Card>
        </div>
      )}

      {/* Simulation Controls */}
      <Card>
        <CardBody>
          <h2 className="font-semibold text-gray-900 mb-3">Simulate Events</h2>
          <div className="mb-4">
            <select
              value={selectedZone}
              onChange={(e) => setSelectedZone(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a zone</option>
              {zones.map((zone) => (
                <option key={zone.id} value={zone.id}>
                  {zone.city} - {zone.name} (Risk: {zone.risk_score.toFixed(0)})
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {TRIGGER_TYPES.map((t) => (
              <Button
                key={t.type}
                onClick={() => simulateEvent(t.type)}
                disabled={simulating || !selectedZone}
                variant="secondary"
                className="text-sm"
              >
                {t.icon} {t.label}
              </Button>
            ))}
          </div>
        </CardBody>
      </Card>

      {/* Active Triggers */}
      <Card>
        <CardBody>
          <h2 className="font-semibold text-gray-900 mb-3">
            Active Triggers ({triggers.length})
          </h2>
          {triggers.length === 0 ? (
            <p className="text-gray-500 text-sm">No active triggers</p>
          ) : (
            <div className="space-y-2">
              {triggers.map((trigger) => (
                <div
                  key={trigger.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div>
                    <span className="font-medium">
                      {trigger.zone_name} - {trigger.trigger_type}
                    </span>
                    <span className="ml-2 text-sm text-gray-500">
                      Severity: {trigger.severity}/5
                    </span>
                  </div>
                  <Button
                    onClick={() => handleProcessTrigger(trigger.id)}
                    size="sm"
                  >
                    Process Claims
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Claims Queue */}
      <Card>
        <CardBody>
          <h2 className="font-semibold text-gray-900 mb-3">
            Recent Claims ({claims.length})
          </h2>
          {claims.length === 0 ? (
            <p className="text-gray-500 text-sm">No claims yet</p>
          ) : (
            <div className="space-y-2">
              {claims.slice(0, 10).map((claim) => (
                <div
                  key={claim.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{claim.partner_name}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[claim.status]}`}>
                        {claim.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">
                      {claim.zone_name} - {claim.trigger_type} - Rs {claim.amount}
                    </p>
                    <p className="text-xs text-gray-400">
                      Fraud score: {(claim.fraud_score * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="flex gap-1">
                    {claim.status === 'pending' && (
                      <>
                        <Button
                          onClick={() => handleClaimAction(claim.id, 'approve')}
                          size="sm"
                        >
                          Approve
                        </Button>
                        <Button
                          onClick={() => handleClaimAction(claim.id, 'reject')}
                          size="sm"
                          variant="secondary"
                        >
                          Reject
                        </Button>
                      </>
                    )}
                    {claim.status === 'approved' && (
                      <Button
                        onClick={() => handleClaimAction(claim.id, 'payout')}
                        size="sm"
                      >
                        Pay Out
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Zones List */}
      <Card>
        <CardBody>
          <h2 className="font-semibold text-gray-900 mb-3">
            Zones ({zones.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {zones.map((zone) => (
              <div
                key={zone.id}
                className="p-3 bg-gray-50 rounded-lg"
              >
                <div className="font-medium">{zone.name}</div>
                <div className="text-sm text-gray-500">{zone.city} - {zone.code}</div>
                <div className="text-xs text-gray-400">
                  Risk Score: {zone.risk_score.toFixed(1)}
                </div>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
