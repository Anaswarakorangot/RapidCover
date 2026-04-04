import React from 'react';

export default function OfflineFallbackCard() {
  return (
    <div style={{
      background: '#fffbeb',
      border: '1.5px solid #fde68a',
      borderRadius: '16px',
      padding: '16px',
      marginBottom: '16px',
      display: 'flex',
      gap: '12px',
      alignItems: 'flex-start',
      fontFamily: "'DM Sans', sans-serif"
    }}>
      <div style={{
        background: '#fef3c7',
        width: 40,
        height: 40,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
      }}>
        <span style={{ fontSize: '20px' }}>📶</span>
      </div>
      <div>
        <h3 style={{ 
          margin: 0, 
          fontFamily: "'Nunito', sans-serif", 
          fontSize: '16px', 
          fontWeight: 800, 
          color: '#92400e',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          Connection Lost
          <span style={{
            fontSize: '10px',
            background: '#ef4444',
            color: 'white',
            padding: '2px 6px',
            borderRadius: '12px',
            textTransform: 'uppercase',
            fontWeight: 800
          }}>Offline</span>
        </h3>
        <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#b45309', lineHeight: 1.4 }}>
          Don't worry! Your active coverage is protected. Any triggered claims will process server-side automatically. <strong>You will receive an SMS via our fallback channel.</strong>
        </p>
      </div>
    </div>
  );
}
