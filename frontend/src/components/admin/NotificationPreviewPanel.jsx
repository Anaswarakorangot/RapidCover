// frontend/src/components/admin/NotificationPreviewPanel.jsx
// Dynamic notification template preview — fetches templates and renders live previews

import { useState, useEffect } from 'react';
import { AdminLoader, AdminError, AdminEmpty, ProofCard } from './AdminProofShared';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function NotificationPreviewPanel() {
  const [templates, setTemplates] = useState(null);
  const [preview, setPreview]     = useState(null);
  const [loading, setLoading]     = useState(true);
  const [previewing, setPreviewing] = useState(false);
  const [sending, setSending]       = useState(false);
  const [error, setError]         = useState(null);
  const [testPhone, setTestPhone] = useState(localStorage.getItem('user_phone') || '');
  const [lastResponse, setLastResponse] = useState(null);

  const [selectedType, setSelectedType] = useState('claim_created');
  const [selectedLang, setSelectedLang] = useState('en');

  async function loadTemplates() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/admin/panel/notifications/templates`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTemplates(data);
      // Set first type as default
      if (data.notification_types?.length > 0) {
        setSelectedType(data.notification_types[0]);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadPreview() {
    setPreviewing(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${API}/admin/panel/notifications/preview?type=${selectedType}&lang=${selectedLang}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setPreview(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setPreviewing(false);
    }
  }

  async function handleSendTest() {
    if (!testPhone) {
        setLastResponse({ success: false, message: 'Please enter a phone number' });
        return;
    }
    setSending(true);
    setLastResponse(null);
    try {
      // Use relative path to leverage Vite proxy and avoid CORS/Auth issues
      const res = await fetch(`/api/v1/admin/test-push?phone=${encodeURIComponent(testPhone)}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to send test push');
      
      if (data.devices === 0) {
        setLastResponse({ 
            success: true, 
            message: `⚠️ Found 0 active devices for ${testPhone}. Ask the partner to click "Enable Alerts" on their Dashboard first!` 
        });
      } else {
        setLastResponse({ 
            success: true, 
            message: `🚀 Push sent to ${data.devices} devices associated with ${testPhone}!` 
        });
      }
    } catch (e) {
      setLastResponse({ success: false, message: e.message });
    } finally {
      setSending(false);
    }
  }

  useEffect(() => { loadTemplates(); }, []);
  useEffect(() => { if (templates) loadPreview(); }, [selectedType, selectedLang]);

  if (loading) return <AdminLoader message="Loading notification templates…" />;
  if (error)   return <AdminError message={error} onRetry={loadTemplates} />;
  if (!templates) return <AdminEmpty icon="🔔" message="No notification templates" />;

  const types = templates.notification_types || [];
  const langs = templates.supported_languages || ['en', 'hi'];
  const allTemplates = templates.templates || {};

  return (
    <ProofCard
      title="🔔 Notification Preview"
      subtitle={`${types.length} notification types · ${langs.length} languages`}
      source="config"
      passFail="pass"
    >
      {/* Controls */}
      <div className="notif-controls">
        <div className="notif-control-group">
          <label className="notif-control-label">Notification Type</label>
          <select className="notif-select" value={selectedType} onChange={e => setSelectedType(e.target.value)}>
            {types.map(t => (
              <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
        <div className="notif-control-group">
          <label className="notif-control-label">Language</label>
          <select className="notif-select" value={selectedLang} onChange={e => setSelectedLang(e.target.value)}>
            {langs.map(l => (
              <option key={l} value={l}>{l === 'en' ? '🇬🇧 English' : l === 'hi' ? '🇮🇳 Hindi' : l}</option>
            ))}
          </select>
        </div>
        <div className="notif-control-group">
          <label className="notif-control-label">Test Phone Number</label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input 
              type="text" 
              className="notif-select" 
              placeholder="e.g. 9876543210" 
              value={testPhone} 
              onChange={e => setTestPhone(e.target.value)}
              style={{ width: '150px' }}
            />
            <button 
              className="admin-btn" 
              onClick={handleSendTest} 
              disabled={sending}
              style={{ 
                height: '38px', 
                whiteSpace: 'nowrap',
                background: sending ? 'var(--text-light)' : '#22c55e',
                color: 'white',
                border: 'none',
                fontWeight: 700
              }}
            >
              {sending ? 'Sending...' : '🚀 Send Push'}
            </button>
          </div>
        </div>
      </div>

      {lastResponse && (
        <div style={{ 
          marginTop: '1rem', 
          padding: '0.75rem', 
          borderRadius: '8px', 
          fontSize: '0.85rem',
          backgroundColor: lastResponse.success ? 'var(--green-light)' : '#fef2f2',
          color: lastResponse.success ? 'var(--green-dark)' : '#dc2626',
          border: `1px solid ${lastResponse.success ? 'var(--green-primary)' : '#fecaca'}`,
          fontWeight: 600
        }}>
          {lastResponse.success ? '✅' : '❌'} {lastResponse.message}
          {!lastResponse.success && lastResponse.message.includes('404') && (
            <p style={{ fontWeight: 400, marginTop: '4px', fontSize: '0.8rem' }}>
              Tip: Go to the Dashboard and click "Enable Alerts" first!
            </p>
          )}
        </div>
      )}

      {/* Preview card */}
      <div className="notif-preview-card" style={{ marginTop: '1.5rem' }}>
        {previewing ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-light)' }}>
            Loading preview…
          </div>
        ) : preview ? (
          <>
            <div className="notif-preview-header">
              <span className="notif-preview-icon">🔔</span>
              <div>
                <p className="notif-preview-title">{preview.title}</p>
                <p className="notif-preview-body">{preview.body}</p>
              </div>
            </div>
            {preview.data && (
              <div className="notif-preview-data">
                <p className="proof-detail-section-label" style={{ marginTop: '1rem' }}>PAYLOAD DATA</p>
                <div className="proof-formula-grid">
                  {Object.entries(preview.data).map(([k, v]) => (
                    <div key={k} className="proof-formula-step">
                      <span className="proof-formula-step__label">{k}</span>
                      <code className="proof-formula-step__value">{String(v)}</code>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <p style={{ color: 'var(--text-light)', textAlign: 'center', padding: '2rem' }}>
            Select a type and language to preview
          </p>
        )}
      </div>

      {/* Template inventory */}
      <div style={{ marginTop: '2rem' }}>
        <p className="proof-detail-section-label">TEMPLATE INVENTORY</p>
        <div className="proof-table-wrapper">
          <table className="proof-table">
            <thead>
              <tr>
                <th>Type</th>
                {langs.map(l => <th key={l} style={{ textAlign: 'center' }}>{l.toUpperCase()}</th>)}
              </tr>
            </thead>
            <tbody>
              {types.map(t => (
                <tr key={t}>
                  <td style={{ fontWeight: 700, fontSize: '0.85rem' }}>{t.replace(/_/g, ' ')}</td>
                  {langs.map(l => (
                    <td key={l} style={{ textAlign: 'center' }}>
                      {allTemplates[t]?.[l] ? (
                        <span style={{ color: 'var(--green-primary)', fontWeight: 900 }}>✓</span>
                      ) : (
                        <span style={{ color: 'var(--text-light)' }}>—</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </ProofCard>
  );
}
