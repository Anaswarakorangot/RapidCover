import React from 'react';

export default function HelpSupportPanel() {
  return (
    <div style={{ fontFamily: "'DM Sans', sans-serif", color: 'var(--text-dark)' }}>
      <p style={{ fontSize: 13, color: 'var(--text-mid)', marginBottom: 20 }}>
        Need help? Our AI assistant and dedicated support team are here for you 24/7.
      </p>

      {/* Support Methods */}
      <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 12px' }}>Contact Options</h3>
      
      <a href="https://wa.me/919999999999" className="support-card" target="_blank" rel="noreferrer" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 12, padding: 16, background: '#f0fdf4', border: '1.5px solid #bbf7d0', borderRadius: 16, marginBottom: 12 }}>
        <div style={{ fontSize: 24 }}>💬</div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#166534' }}>WhatsApp Support</div>
          <div style={{ fontSize: 13, color: '#15803d', marginTop: 2 }}>Instant live agent reply within 5 mins</div>
        </div>
      </a>

      <a href="mailto:support@rapidcover.in" className="support-card" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 12, padding: 16, background: '#f8fafc', border: '1.5px solid #e2e8f0', borderRadius: 16, marginBottom: 24 }}>
        <div style={{ fontSize: 24 }}>✉️</div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#334155' }}>Email Ticketing</div>
          <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>support@rapidcover.in</div>
        </div>
      </a>

      <hr style={{ border: 'none', borderTop: '1px solid #e2ece2', margin: '24px 0' }} />

      {/* FAQs */}
      <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 16px' }}>Frequently Asked Questions</h3>

      <div style={{ background: '#ffffff', border: '1px solid #e2ece2', borderRadius: 16, overflow: 'hidden' }}>
        <div style={{ padding: 16, borderBottom: '1px solid #e2ece2' }}>
          <h4 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#1a2e1a', marginBottom: 4 }}>How do automatic claims work?</h4>
          <p style={{ margin: 0, fontSize: 13, color: '#4a5e4a', lineHeight: 1.5 }}>
            Our system monitors weather and civic data in real-time. If an event in your active zone crosses our severe threshold, your policy is triggered automatically. You do not need to upload any proof!
          </p>
        </div>
        <div style={{ padding: 16, borderBottom: '1px solid #e2ece2' }}>
          <h4 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#1a2e1a', marginBottom: 4 }}>Payout timing guarantees</h4>
          <p style={{ margin: 0, fontSize: 13, color: '#4a5e4a', lineHeight: 1.5 }}>
            Because claims are verified automatically by server oracles, 95% of payouts are sent to your Stripe or UPI account within <strong>3-4 minutes</strong> of the trigger event conclusion.
          </p>
        </div>
        <div style={{ padding: 16, borderBottom: '1px solid #e2ece2' }}>
          <h4 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#1a2e1a', marginBottom: 4 }}>What if IMPS/UPI transfer fails?</h4>
          <p style={{ margin: 0, fontSize: 13, color: '#4a5e4a', lineHeight: 1.5 }}>
            If your primary UPI payout fails, we automatically attempt the transaction via your submitted IMPS fallback bank account. Failing both, your claim enters the 'reconcile_pending' queue for manual agent payout to your RapidCover wallet.
          </p>
        </div>
        <div style={{ padding: 16 }}>
          <h4 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#1a2e1a', marginBottom: 4 }}>What if the app is offline?</h4>
          <p style={{ margin: 0, fontSize: 13, color: '#4a5e4a', lineHeight: 1.5 }}>
            Even if your phone dies or loses connection, your locked-in coverage continues. We process the trigger server-side, and you will immediately receive an SMS confirmation via our Offline Fallback system.
          </p>
        </div>
      </div>
    </div>
  );
}
