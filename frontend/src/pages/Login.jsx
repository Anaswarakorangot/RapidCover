import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input, OTPInput, Card, CardBody } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [step, setStep] = useState('phone'); // phone | otp
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [devOtp, setDevOtp] = useState(''); // Show OTP for dev
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleRequestOTP(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    const cleanPhone = phone.replace(/\s/g, '');
    try {
      const result = await api.requestOTP(cleanPhone);
      // In dev mode, OTP is returned in response - show it on screen
      if (result.otp) {
        setDevOtp(result.otp);
        setOtp(result.otp); // Auto-fill for convenience
      }
      setStep('otp');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOTP(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    const cleanPhone = phone.replace(/\s/g, '');
    try {
      await login(cleanPhone, otp);
      navigate('/');
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
        <h1 className="text-2xl font-bold text-gray-900 mt-4">RapidCover</h1>
        <p className="text-gray-600 mt-2">Income protection for delivery partners</p>
      </div>

      <Card className="w-full max-w-sm">
        <CardBody>
          {step === 'phone' ? (
            <form onSubmit={handleRequestOTP}>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Enter your phone number
              </h2>
              <Input
                type="tel"
                placeholder="+91 9876543210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                error={error}
              />
              <Button
                type="submit"
                className="w-full mt-4"
                loading={loading}
                disabled={phone.length < 10}
              >
                Get OTP
              </Button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOTP}>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Enter OTP
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                Sent to {phone}
              </p>
              {devOtp && (
                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-xs text-yellow-700">Dev Mode - Your OTP:</p>
                  <p className="text-2xl font-mono font-bold text-yellow-800">{devOtp}</p>
                </div>
              )}
              <OTPInput value={otp} onChange={setOtp} />
              {error && (
                <p className="mt-2 text-sm text-red-600 text-center">{error}</p>
              )}
              <Button
                type="submit"
                className="w-full mt-4"
                loading={loading}
                disabled={otp.length < 6}
              >
                Verify & Login
              </Button>
              <button
                type="button"
                onClick={() => setStep('phone')}
                className="w-full mt-2 text-sm text-blue-600 hover:underline"
              >
                Change phone number
              </button>
            </form>
          )}
        </CardBody>
      </Card>

      <p className="mt-6 text-sm text-gray-500">
        New here?{' '}
        <a href="/register" className="text-blue-600 hover:underline">
          Register now
        </a>
      </p>
    </div>
  );
}
