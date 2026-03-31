import { useState, useEffect } from 'react';
import { Card, CardBody, CardFooter, Button } from '../components/ui';
import api from '../services/api';

const TIER_ICONS = {
  flex: '🌱',
  standard: '⭐',
  pro: '👑',
};

export function Policy() {
  const [quotes, setQuotes] = useState([]);
  const [activePolicy, setActivePolicy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [quotesData, policyData] = await Promise.all([
        api.getPolicyQuotes(),
        api.getActivePolicy().catch(() => null),
      ]);
      setQuotes(quotesData);
      setActivePolicy(policyData);
    } catch (error) {
      console.error('Failed to load policy data:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handlePurchase(tier) {
    setPurchasing(tier);
    try {
      await api.createPolicy(tier);
      await loadData();
    } catch (error) {
      alert(error.message);
    } finally {
      setPurchasing(null);
    }
  }

  async function handleCancel() {
    if (!confirm('Are you sure you want to cancel your policy?')) return;

    try {
      await api.cancelPolicy(activePolicy.id);
      await loadData();
    } catch (error) {
      alert(error.message);
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Insurance Plans</h1>
        <p className="text-gray-600">Choose coverage that fits your needs</p>
      </div>

      {/* Active Policy Banner */}
      {activePolicy && (
        <Card className="bg-green-50 border-green-200">
          <CardBody>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-green-800 font-semibold">
                  Active: {activePolicy.tier.toUpperCase()} Plan
                </p>
                <p className="text-green-600 text-sm">
                  Expires {new Date(activePolicy.expires_at).toLocaleDateString()}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCancel}
                className="text-red-600 border-red-300 hover:bg-red-50"
              >
                Cancel
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Plan Cards */}
      <div className="space-y-4">
        {quotes.map((quote) => {
          const isActive = activePolicy?.tier === quote.tier;
          return (
            <Card
              key={quote.tier}
              className={isActive ? 'ring-2 ring-blue-500' : ''}
            >
              <CardBody>
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-2xl">{TIER_ICONS[quote.tier]}</span>
                    <h3 className="text-xl font-bold text-gray-900 mt-1 capitalize">
                      {quote.tier}
                    </h3>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-gray-900">
                      ₹{quote.final_premium}
                    </p>
                    <p className="text-sm text-gray-500">/week</p>
                    {quote.risk_adjustment !== 0 && (
                      <p className={`text-xs ${quote.risk_adjustment < 0 ? 'text-green-600' : 'text-orange-600'}`}>
                        {quote.risk_adjustment < 0 ? 'Zone discount' : 'Zone surcharge'}: ₹{Math.abs(quote.risk_adjustment)}
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-500">Daily Payout</p>
                    <p className="font-semibold text-gray-900">₹{quote.max_daily_payout}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-500">Max Days/Week</p>
                    <p className="font-semibold text-gray-900">{quote.max_days_per_week}</p>
                  </div>
                </div>
              </CardBody>
              <CardFooter>
                <Button
                  className="w-full"
                  variant={isActive ? 'secondary' : 'primary'}
                  disabled={!!activePolicy || purchasing === quote.tier}
                  loading={purchasing === quote.tier}
                  onClick={() => handlePurchase(quote.tier)}
                >
                  {isActive ? 'Current Plan' : activePolicy ? 'Already Covered' : 'Get This Plan'}
                </Button>
              </CardFooter>
            </Card>
          );
        })}
      </div>

      {/* Info */}
      <Card>
        <CardBody className="text-sm text-gray-600">
          <h4 className="font-semibold text-gray-900 mb-2">How it works:</h4>
          <ul className="space-y-1 list-disc list-inside">
            <li>Pay weekly premium via UPI</li>
            <li>Automatic payout when trigger events occur</li>
            <li>No claim forms - we detect events automatically</li>
            <li>Money credited to your UPI within minutes</li>
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
