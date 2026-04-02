import { useState, useEffect } from 'react';
import { Card, CardBody, CardFooter, Button } from '../components/ui';
import api from '../services/api';

const TIER_ICONS = {
  flex: '🌱',
  standard: '⭐',
  pro: '👑',
};

const STATUS_STYLES = {
  active: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    badge: 'bg-green-100 text-green-800',
    text: 'text-green-800',
    subtext: 'text-green-600',
  },
  grace_period: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    badge: 'bg-yellow-100 text-yellow-800',
    text: 'text-yellow-800',
    subtext: 'text-yellow-600',
  },
  lapsed: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-100 text-red-800',
    text: 'text-red-800',
    subtext: 'text-red-600',
  },
  cancelled: {
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    badge: 'bg-gray-100 text-gray-800',
    text: 'text-gray-800',
    subtext: 'text-gray-600',
  },
};

const STATUS_LABELS = {
  active: 'Active',
  grace_period: 'Grace Period',
  lapsed: 'Lapsed',
  cancelled: 'Cancelled',
};

export function Policy() {
  const [quotes, setQuotes] = useState([]);
  const [activePolicy, setActivePolicy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);
  const [showRenewalModal, setShowRenewalModal] = useState(false);
  const [renewalQuote, setRenewalQuote] = useState(null);
  const [selectedRenewalTier, setSelectedRenewalTier] = useState(null);
  const [renewalLoading, setRenewalLoading] = useState(false);
  const [downloadingCert, setDownloadingCert] = useState(false);
  const [togglingAutoRenew, setTogglingAutoRenew] = useState(false);

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

  async function openRenewalModal() {
    setShowRenewalModal(true);
    setSelectedRenewalTier(activePolicy?.tier || null);
    setRenewalLoading(true);
    try {
      const quote = await api.getRenewalQuote(activePolicy.id, selectedRenewalTier);
      setRenewalQuote(quote);
    } catch (error) {
      console.error('Failed to get renewal quote:', error);
      alert(error.message);
      setShowRenewalModal(false);
    } finally {
      setRenewalLoading(false);
    }
  }

  async function handleTierChange(tier) {
    setSelectedRenewalTier(tier);
    setRenewalLoading(true);
    try {
      const quote = await api.getRenewalQuote(activePolicy.id, tier);
      setRenewalQuote(quote);
    } catch (error) {
      console.error('Failed to get renewal quote:', error);
    } finally {
      setRenewalLoading(false);
    }
  }

  async function handleRenew() {
    setRenewalLoading(true);
    try {
      await api.renewPolicy(
        activePolicy.id,
        selectedRenewalTier !== activePolicy.tier ? selectedRenewalTier : null,
        activePolicy.auto_renew
      );
      setShowRenewalModal(false);
      setRenewalQuote(null);
      await loadData();
    } catch (error) {
      alert(error.message);
    } finally {
      setRenewalLoading(false);
    }
  }

  async function handleDownloadCertificate() {
    setDownloadingCert(true);
    try {
      await api.downloadCertificate(activePolicy.id);
    } catch (error) {
      alert(error.message);
    } finally {
      setDownloadingCert(false);
    }
  }

  async function handleToggleAutoRenew() {
    setTogglingAutoRenew(true);
    try {
      await api.toggleAutoRenew(activePolicy.id, !activePolicy.auto_renew);
      await loadData();
    } catch (error) {
      alert(error.message);
    } finally {
      setTogglingAutoRenew(false);
    }
  }

  function formatCountdown() {
    if (!activePolicy) return null;

    if (activePolicy.status === 'active' && activePolicy.days_until_expiry !== null) {
      if (activePolicy.days_until_expiry === 0) {
        return 'Expires today';
      } else if (activePolicy.days_until_expiry === 1) {
        return 'Expires tomorrow';
      } else {
        return `Expires in ${activePolicy.days_until_expiry} days`;
      }
    }

    if (activePolicy.status === 'grace_period' && activePolicy.hours_until_grace_ends !== null) {
      const hours = Math.floor(activePolicy.hours_until_grace_ends);
      if (hours < 1) {
        return 'Grace period ending soon';
      } else if (hours === 1) {
        return 'Grace period: 1 hour left';
      } else {
        return `Grace period: ${hours}h left`;
      }
    }

    return null;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const policyStatus = activePolicy?.status || 'active';
  const statusStyle = STATUS_STYLES[policyStatus] || STATUS_STYLES.active;
  const countdown = formatCountdown();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Insurance Plans</h1>
        <p className="text-gray-600">Choose coverage that fits your needs</p>
      </div>

      {/* Active Policy Banner */}
      {activePolicy && (
        <Card className={`${statusStyle.bg} ${statusStyle.border}`}>
          <CardBody>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <p className={`${statusStyle.text} font-semibold`}>
                    {activePolicy.tier.toUpperCase()} Plan
                  </p>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusStyle.badge}`}>
                    {STATUS_LABELS[policyStatus]}
                  </span>
                </div>
                <p className={`${statusStyle.subtext} text-sm`}>
                  {countdown || `Expires ${new Date(activePolicy.expires_at).toLocaleDateString()}`}
                </p>

                {/* Auto-renewal toggle */}
                <div className="flex items-center gap-2 mt-3">
                  <button
                    onClick={handleToggleAutoRenew}
                    disabled={togglingAutoRenew}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                      activePolicy.auto_renew ? 'bg-blue-600' : 'bg-gray-200'
                    } ${togglingAutoRenew ? 'opacity-50' : ''}`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        activePolicy.auto_renew ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                  <span className="text-sm text-gray-600">Auto-renewal</span>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                {/* Renew button */}
                {activePolicy.can_renew && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={openRenewalModal}
                  >
                    Renew
                  </Button>
                )}

                {/* Download certificate */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadCertificate}
                  disabled={downloadingCert}
                  loading={downloadingCert}
                >
                  Certificate
                </Button>

                {/* Cancel button */}
                {policyStatus === 'active' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCancel}
                    className="text-red-600 border-red-300 hover:bg-red-50"
                  >
                    Cancel
                  </Button>
                )}
              </div>
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
                    <h3 className="text-xl font-bold text-gray-900 mt-1">
                      {quote.tier_label || quote.tier.charAt(0).toUpperCase() + quote.tier.slice(1)}
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

                <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-400 uppercase font-semibold">Max Day Payout</p>
                    <p className="font-bold text-gray-900 text-sm">₹{quote.max_daily_payout}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-400 uppercase font-semibold">Max Days/Week</p>
                    <p className="font-bold text-gray-900 text-sm">{quote.max_days_per_week}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-400 uppercase font-semibold">Max Weekly</p>
                    <p className="font-bold text-blue-600 text-sm">₹{quote.max_daily_payout * quote.max_days_per_week}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-400 uppercase font-semibold">Benefit Ratio</p>
                    <p className="font-bold text-green-600 text-sm">~1:{Math.round((quote.max_daily_payout * quote.max_days_per_week) / quote.final_premium)}</p>
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
            <li>48-hour grace period after expiry for renewal</li>
          </ul>
        </CardBody>
      </Card>

      {/* Renewal Modal */}
      {showRenewalModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Renew Your Policy</h3>

            {/* Tier selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Plan
              </label>
              <div className="grid grid-cols-3 gap-2">
                {quotes.map((quote) => (
                  <button
                    key={quote.tier}
                    onClick={() => handleTierChange(quote.tier)}
                    className={`p-3 rounded-lg border-2 text-center transition-colors ${
                      selectedRenewalTier === quote.tier
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <span className="text-xl">{TIER_ICONS[quote.tier]}</span>
                    <p className="text-sm font-medium capitalize">{quote.tier}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Quote details */}
            {renewalLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
              </div>
            ) : renewalQuote ? (
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Base Premium</span>
                    <span>₹{renewalQuote.base_premium}</span>
                  </div>
                  {renewalQuote.risk_adjustment !== 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Zone Adjustment</span>
                      <span className={renewalQuote.risk_adjustment < 0 ? 'text-green-600' : 'text-orange-600'}>
                        {renewalQuote.risk_adjustment < 0 ? '-' : '+'}₹{Math.abs(renewalQuote.risk_adjustment)}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between text-green-600">
                    <span>Loyalty Discount (5%)</span>
                    <span>-₹{renewalQuote.loyalty_discount}</span>
                  </div>
                  <div className="border-t pt-2 flex justify-between font-semibold">
                    <span>Total</span>
                    <span className="text-lg">₹{renewalQuote.final_premium}/week</span>
                  </div>
                </div>
              </div>
            ) : null}

            {/* Actions */}
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => {
                  setShowRenewalModal(false);
                  setRenewalQuote(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="flex-1"
                onClick={handleRenew}
                disabled={renewalLoading || !renewalQuote}
                loading={renewalLoading}
              >
                Confirm Renewal
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
