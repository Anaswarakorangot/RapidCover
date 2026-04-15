import React, { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

const CATEGORY_ICONS = {
  Compliance: '🛡️',
  Operational: '⚡',
  System: '⚙️',
  Integration: '🔗'
};

export function SettingsPanel() {
  const [settings, setSettings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  async function fetchSettings() {
    try {
      const res = await fetch(`${API_BASE}/admin/panel/settings`);
      const data = await res.json();
      setSettings(data);
    } catch (err) {
      console.error("Failed to fetch settings", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/admin/panel/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings })
      });
      if (res.ok) {
        setMessage({ type: 'success', text: 'Configuration saved successfully' });
        setTimeout(() => setMessage(null), 5000);
      } else {
        throw new Error("Save failed");
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to update system configuration' });
    } finally {
      setSaving(false);
    }
  }

  const updateValue = (key, value) => {
    setSettings(prev => prev.map(s => s.key === key ? { ...s, value } : s));
  };

  if (loading) return (
    <div className="admin-loader">
      <div className="admin-loader__spinner" />
      <span>Fetching system configs...</span>
    </div>
  );

  const categories = [...new Set(settings.map(s => s.category))];

  return (
    <div className="settings-panel-architect fade-in">
      <header className="settings-header">
        <div>
          <h2 className="settings-title">System Settings</h2>
          <p className="settings-subtitle">Manage global insurance rules, operational thresholds, and system connectivity.</p>
        </div>
        <button 
          className="admin-btn admin-btn--primary premium-btn" 
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
      </header>

      {message && (
        <div className={`settings-toast settings-toast--${message.type}`}>
          <span className="toast-icon">{message.type === 'success' ? '✅' : '❌'}</span>
          {message.text}
        </div>
      )}

      <div className="settings-grid-layout">
        {categories.map(cat => (
          <div key={cat} className="settings-card-premium">
            <div className="settings-card-header">
              <span className="category-icon">{CATEGORY_ICONS[cat] || '📁'}</span>
              <h3 className="category-title">{cat}</h3>
            </div>
            
            <div className="settings-rows">
              {settings.filter(s => s.category === cat).map(setting => (
                <div key={setting.key} className="setting-row-premium">
                  <div className="setting-meta">
                    <label className="setting-label-text">
                      {setting.key.split('_').slice(1).join(' ').toUpperCase()}
                    </label>
                    <span className="setting-desc-text">{setting.description}</span>
                  </div>
                  
                  <div className="setting-action">
                    {setting.value === 'true' || setting.value === 'false' ? (
                      <button 
                        className={`modern-toggle ${setting.value === 'true' ? 'modern-toggle--active' : ''}`}
                        onClick={() => updateValue(setting.key, setting.value === 'true' ? 'false' : 'true')}
                      >
                        <div className="modern-toggle-thumb"></div>
                      </button>
                    ) : (
                      <input 
                        type="text" 
                        className="modern-input" 
                        value={setting.value}
                        onChange={(e) => updateValue(setting.key, e.target.value)}
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
