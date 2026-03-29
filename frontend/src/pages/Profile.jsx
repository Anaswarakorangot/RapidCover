import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardBody, Button, Input } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { NotificationToggle } from '../components/NotificationToggle';
import api from '../services/api';

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी (Hindi)' },
  { code: 'ta', label: 'தமிழ் (Tamil)' },
  { code: 'kn', label: 'ಕನ್ನಡ (Kannada)' },
  { code: 'te', label: 'తెలుగు (Telugu)' },
  { code: 'mr', label: 'मराठी (Marathi)' },
  { code: 'bn', label: 'বাংলা (Bengali)' },
];

export function Profile() {
  const navigate = useNavigate();
  const { user, logout, refreshUser } = useAuth();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user?.name || '');
  const [language, setLanguage] = useState(user?.language_pref || 'en');
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await api.updateProfile({ name, language_pref: language });
      await refreshUser();
      setEditing(false);
    } catch (error) {
      alert(error.message);
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        <p className="text-gray-600">Manage your account</p>
      </div>

      {/* Profile Info */}
      <Card>
        <CardBody className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-2xl">👤</span>
            </div>
            <div>
              <p className="font-semibold text-gray-900">{user?.name}</p>
              <p className="text-sm text-gray-500">{user?.phone}</p>
              <p className="text-xs text-gray-400 capitalize">{user?.platform} Partner</p>
            </div>
          </div>

          {editing ? (
            <>
              <Input
                label="Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => setEditing(false)}
                >
                  Cancel
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleSave}
                  loading={saving}
                >
                  Save
                </Button>
              </div>
            </>
          ) : (
            <Button
              variant="outline"
              className="w-full"
              onClick={() => setEditing(true)}
            >
              Edit Profile
            </Button>
          )}
        </CardBody>
      </Card>

      {/* Zone Info */}
      {user?.zone_id && (
        <Card>
          <CardBody>
            <h3 className="font-semibold text-gray-900 mb-2">Your Zone</h3>
            <p className="text-gray-600">Zone ID: {user.zone_id}</p>
          </CardBody>
        </Card>
      )}

      {/* Notifications */}
      <Card>
        <CardBody>
          <h3 className="font-semibold text-gray-900 mb-2">Notifications</h3>
          <NotificationToggle />
        </CardBody>
      </Card>

      {/* Account Actions */}
      <Card>
        <CardBody className="space-y-3">
          <button className="w-full text-left py-2 text-gray-700 hover:text-gray-900 flex items-center justify-between">
            <span>📄 Terms of Service</span>
            <span className="text-gray-400">→</span>
          </button>
          <button className="w-full text-left py-2 text-gray-700 hover:text-gray-900 flex items-center justify-between">
            <span>🔒 Privacy Policy</span>
            <span className="text-gray-400">→</span>
          </button>
          <button className="w-full text-left py-2 text-gray-700 hover:text-gray-900 flex items-center justify-between">
            <span>💬 Help & Support</span>
            <span className="text-gray-400">→</span>
          </button>
        </CardBody>
      </Card>

      {/* Logout */}
      <Button
        variant="danger"
        className="w-full"
        onClick={handleLogout}
      >
        Logout
      </Button>

      <p className="text-center text-xs text-gray-400">
        RapidCover v1.0.0
      </p>
    </div>
  );
}
