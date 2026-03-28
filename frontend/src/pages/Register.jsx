import { useState } from 'react';
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
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
