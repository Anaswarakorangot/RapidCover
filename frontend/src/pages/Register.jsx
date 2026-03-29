import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button, Input, Card, CardBody } from '../components/ui';
import api from '../services/api';

const PLATFORMS = [
  { value: 'zepto', label: 'Zepto' },
  { value: 'blinkit', label: 'Blinkit' },
];

export function Register() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    phone: '',
    name: '',
    platform: 'zepto',
    zone_id: '',
  });
  const [zones, setZones] = useState([]);
  const [zonesLoading, setZonesLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [gpsStatus, setGpsStatus] = useState('idle'); // idle | loading | success | too_far | error | denied
  const [detectedZone, setDetectedZone] = useState(null);

  useEffect(() => {
    async function loadZones() {
      try {
        const zoneData = await api.getZones();
        setZones(zoneData);
      } catch (err) {
        console.error('Failed to load zones:', err);
      } finally {
        setZonesLoading(false);
      }
    }
    loadZones();
  }, []);

  const MAX_DETECTION_DISTANCE_KM = 25;

  async function detectLocation() {
    if (!navigator.geolocation) {
      setGpsStatus('error');
      return;
    }

    setGpsStatus('loading');

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const result = await api.getNearestZones(latitude, longitude);
          if (result.length > 0) {
            const nearest = result[0];
            if (nearest.distance_km <= MAX_DETECTION_DISTANCE_KM) {
              setDetectedZone(nearest);
              setFormData((prev) => ({ ...prev, zone_id: String(nearest.zone.id) }));
              setGpsStatus('success');
            } else {
              setDetectedZone(nearest);
              setGpsStatus('too_far');
            }
          } else {
            setGpsStatus('error');
          }
        } catch (err) {
          console.error('Failed to get nearest zones:', err);
          setGpsStatus('error');
        }
      },
      (error) => {
        setGpsStatus(error.code === 1 ? 'denied' : 'error');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function handleChange(e) {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Clean phone number - remove spaces
      const cleanData = {
        ...formData,
        phone: formData.phone.replace(/\s/g, ''),
        zone_id: formData.zone_id ? parseInt(formData.zone_id, 10) : null,
      };
      await api.register(cleanData);
      // After registration, redirect to login
      navigate('/login');
      alert('Registration successful! Please login.');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <div className="text-center mb-8">
        <span className="text-5xl">🛡️</span>
        <h1 className="text-2xl font-bold text-gray-900 mt-4">Join RapidCover</h1>
        <p className="text-gray-600 mt-2">Get income protection in minutes</p>
      </div>

      <Card className="w-full max-w-sm">
        <CardBody>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Full Name"
              name="name"
              placeholder="Enter your name"
              value={formData.name}
              onChange={handleChange}
              required
            />

            <Input
              label="Phone Number"
              name="phone"
              type="tel"
              placeholder="+91 9876543210"
              value={formData.phone}
              onChange={handleChange}
              required
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Platform
              </label>
              <select
                name="platform"
                value={formData.platform}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {PLATFORMS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Dark Store Zone
              </label>

              <button
                type="button"
                onClick={detectLocation}
                disabled={gpsStatus === 'loading' || zonesLoading}
                className="w-full mb-2 px-3 py-2 bg-green-50 border border-green-300 rounded-lg text-green-700 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {gpsStatus === 'loading' ? (
                  <>
                    <span className="animate-spin">&#9696;</span>
                    Detecting location...
                  </>
                ) : (
                  <>
                    <span>&#128205;</span>
                    Detect My Zone
                  </>
                )}
              </button>

              {gpsStatus === 'success' && detectedZone && (
                <p className="text-sm text-green-600 mb-2">
                  Detected: {detectedZone.zone.name} ({detectedZone.distance_km} km away)
                </p>
              )}

              {gpsStatus === 'too_far' && detectedZone && (
                <p className="text-sm text-amber-600 mb-2">
                  No zones near your location. Nearest is {detectedZone.zone.name} ({detectedZone.distance_km} km away). Please select manually.
                </p>
              )}

              {gpsStatus === 'denied' && (
                <p className="text-sm text-amber-600 mb-2">
                  Location access denied. Please select zone manually.
                </p>
              )}

              {gpsStatus === 'error' && (
                <p className="text-sm text-red-600 mb-2">
                  Could not detect location. Please select zone manually.
                </p>
              )}

              <select
                name="zone_id"
                value={formData.zone_id}
                onChange={handleChange}
                disabled={zonesLoading}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              >
                {zonesLoading ? (
                  <option value="">Loading zones...</option>
                ) : zones.length === 0 ? (
                  <option value="">No zones available - contact admin</option>
                ) : (
                  <>
                    <option value="">Select your zone</option>
                    {zones.map((zone) => (
                      <option key={zone.id} value={zone.id}>
                        {zone.city} - {zone.name} ({zone.code})
                      </option>
                    ))}
                  </>
                )}
              </select>
              <p className="text-xs text-gray-500 mt-1">
                {gpsStatus === 'success'
                  ? 'Zone auto-detected. You can change it if needed.'
                  : gpsStatus === 'too_far'
                  ? 'Select from available zones below'
                  : 'Use GPS detection or choose manually'}
              </p>
            </div>

            {error && (
              <p className="text-sm text-red-600">{error}</p>
            )}

            <Button
              type="submit"
              className="w-full"
              loading={loading}
              disabled={!formData.name || !formData.phone}
            >
              Register
            </Button>
          </form>
        </CardBody>
      </Card>

      <p className="mt-6 text-sm text-gray-500">
        Already registered?{' '}
        <Link to="/login" className="text-blue-600 hover:underline">
          Login here
        </Link>
      </p>
    </div>
  );
}
