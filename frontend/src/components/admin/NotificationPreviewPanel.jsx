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
  const [error, setError]         = useState(null);

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
      const res = await fetch(`${API}/admin/panel/notifications/preview?type=${selectedType}&lang=${selectedLang}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setPreview(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setPreviewing(false);
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
      </div>

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
