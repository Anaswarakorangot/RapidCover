import React from 'react';
// src/components/ui/UpiSelector.jsx
// Drop at frontend/src/components/ui/UpiSelector.jsx

const UPI_HANDLES = [
    // ── Major Banks ──────────────────────────────────────────
    { handle: '@okicici', label: 'ICICI Bank', app: '🏦' },
    { handle: '@icicipay', label: 'ICICI Pay', app: '🏦' },
    { handle: '@ibl', label: 'ICICI Bank (ibl)', app: '🏦' },
    { handle: '@oksbi', label: 'State Bank of India', app: '🏦' },
    { handle: '@sbi', label: 'SBI Pay', app: '🏦' },
    { handle: '@okaxis', label: 'Axis Bank', app: '🏦' },
    { handle: '@axis', label: 'Axis Bank (axis)', app: '🏦' },
    { handle: '@axisbank', label: 'Axis Bank (axisbank)', app: '🏦' },
    { handle: '@okhdfcbank', label: 'HDFC Bank', app: '🏦' },
    { handle: '@hdfc', label: 'HDFC (hdfc)', app: '🏦' },
    { handle: '@hdfcbank', label: 'HDFC Bank (hdfcbank)', app: '🏦' },
    { handle: '@kotak', label: 'Kotak Mahindra Bank', app: '🏦' },
    { handle: '@okkotak', label: 'Kotak (okkotak)', app: '🏦' },
    { handle: '@kaypay', label: 'Kotak Kay Pay', app: '🏦' },
    { handle: '@pnb', label: 'Punjab National Bank', app: '🏦' },
    { handle: '@punb', label: 'PNB (punb)', app: '🏦' },
    { handle: '@boi', label: 'Bank of India', app: '🏦' },
    { handle: '@bob', label: 'Bank of Baroda', app: '🏦' },
    { handle: '@barb', label: 'Bank of Baroda (barb)', app: '🏦' },
    { handle: '@union', label: 'Union Bank of India', app: '🏦' },
    { handle: '@unionbank', label: 'Union Bank', app: '🏦' },
    { handle: '@cbin', label: 'Central Bank', app: '🏦' },
    { handle: '@cnrb', label: 'Canara Bank', app: '🏦' },
    { handle: '@indianbank', label: 'Indian Bank', app: '🏦' },
    { handle: '@indbank', label: 'Indian Bank (indbank)', app: '🏦' },
    { handle: '@iob', label: 'Indian Overseas Bank', app: '🏦' },
    { handle: '@andb', label: 'Andhra Bank', app: '🏦' },
    { handle: '@idbi', label: 'IDBI Bank', app: '🏦' },
    { handle: '@idbibank', label: 'IDBI Bank (idbibank)', app: '🏦' },
    { handle: '@federal', label: 'Federal Bank', app: '🏦' },
    { handle: '@fbl', label: 'Federal Bank (fbl)', app: '🏦' },
    { handle: '@yesbank', label: 'Yes Bank', app: '🏦' },
    { handle: '@yesbankltd', label: 'Yes Bank Ltd', app: '🏦' },
    { handle: '@indusind', label: 'IndusInd Bank', app: '🏦' },
    { handle: '@ikwik', label: 'IndusInd (ikwik)', app: '🏦' },
    { handle: '@rbl', label: 'RBL Bank', app: '🏦' },
    { handle: '@rblbank', label: 'RBL Bank (rblbank)', app: '🏦' },
    { handle: '@kvb', label: 'Karur Vysya Bank', app: '🏦' },
    { handle: '@karnataka', label: 'Karnataka Bank', app: '🏦' },
    { handle: '@kbl', label: 'Karnataka Bank (kbl)', app: '🏦' },
    { handle: '@scb', label: 'Standard Chartered', app: '🏦' },
    { handle: '@sc', label: 'Standard Chartered (sc)', app: '🏦' },
    { handle: '@hsbc', label: 'HSBC Bank', app: '🏦' },
    { handle: '@citibank', label: 'Citi Bank', app: '🏦' },
    { handle: '@dcb', label: 'DCB Bank', app: '🏦' },
    { handle: '@dlb', label: 'Dhanlaxmi Bank', app: '🏦' },
    { handle: '@saraswat', label: 'Saraswat Bank', app: '🏦' },
    { handle: '@tjsb', label: 'Thane Janata Bank', app: '🏦' },
    { handle: '@vijb', label: 'Vijaya Bank', app: '🏦' },
    { handle: '@corporation', label: 'Corporation Bank', app: '🏦' },
    { handle: '@allbank', label: 'Allahabad Bank', app: '🏦' },
    { handle: '@syndicatebank', label: 'Syndicate Bank', app: '🏦' },
    { handle: '@uco', label: 'UCO Bank', app: '🏦' },
    { handle: '@uboi', label: 'United Bank of India', app: '🏦' },
    { handle: '@denabank', label: 'Dena Bank', app: '🏦' },
    { handle: '@obc', label: 'Oriental Bank', app: '🏦' },
    { handle: '@aubank', label: 'AU Small Finance Bank', app: '🏦' },
    { handle: '@equitas', label: 'Equitas Small Finance', app: '🏦' },
    { handle: '@esaf', label: 'ESAF Small Finance', app: '🏦' },
    { handle: '@ujjivan', label: 'Ujjivan Small Finance', app: '🏦' },
    { handle: '@janabank', label: 'Jana Small Finance', app: '🏦' },
    { handle: '@suryoday', label: 'Suryoday Bank', app: '🏦' },
    { handle: '@nsdlpay', label: 'NSDL Payments Bank', app: '🏦' },
    { handle: '@airtel', label: 'Airtel Payments Bank', app: '📡' },
    { handle: '@airtelmoney', label: 'Airtel Money', app: '📡' },
    { handle: '@fino', label: 'Fino Payments Bank', app: '🏦' },
    { handle: '@finobank', label: 'Fino Bank', app: '🏦' },
    { handle: '@postbank', label: 'India Post Payments', app: '📮' },
    { handle: '@ippb', label: 'IPPB (ippb)', app: '📮' },

    // ── UPI Apps ─────────────────────────────────────────────
    { handle: '@ybl', label: 'PhonePe (Yes Bank)', app: '📱' },
    { handle: '@axl', label: 'PhonePe (Axis)', app: '📱' },
    { handle: '@idfcfirst', label: 'PhonePe (IDFC)', app: '📱' },
    { handle: '@paytm', label: 'Paytm', app: '📱' },
    { handle: '@ptyes', label: 'Paytm (Yes Bank)', app: '📱' },
    { handle: '@pthdfc', label: 'Paytm (HDFC)', app: '📱' },
    { handle: '@ptsbi', label: 'Paytm (SBI)', app: '📱' },
    { handle: '@ptaxis', label: 'Paytm (Axis)', app: '📱' },
    { handle: '@pticici', label: 'Paytm (ICICI)', app: '📱' },
    { handle: '@gpay', label: 'Google Pay', app: '📱' },
    { handle: '@okaxis', label: 'Google Pay (Axis)', app: '📱' },
    { handle: '@okhdfcbank', label: 'Google Pay (HDFC)', app: '📱' },
    { handle: '@oksbi', label: 'Google Pay (SBI)', app: '📱' },
    { handle: '@okicici', label: 'Google Pay (ICICI)', app: '📱' },
    { handle: '@apl', label: 'Amazon Pay (ICICI)', app: '🛒' },
    { handle: '@yapl', label: 'Amazon Pay (Yes)', app: '🛒' },
    { handle: '@rapl', label: 'Amazon Pay (RBL)', app: '🛒' },
    { handle: '@bhim', label: 'BHIM UPI', app: '🇮🇳' },
    { handle: '@upi', label: 'BHIM UPI (upi)', app: '🇮🇳' },
    { handle: '@naviaxis', label: 'Navi (Axis)', app: '📱' },
    { handle: '@slice', label: 'Slice', app: '📱' },
    { handle: '@sliceaxis', label: 'Slice (Axis)', app: '📱' },
    { handle: '@freecharge', label: 'Freecharge', app: '📱' },
    { handle: '@fcok', label: 'Freecharge (fcok)', app: '📱' },
    { handle: '@mobikwik', label: 'MobiKwik', app: '📱' },
    { handle: '@ikwik', label: 'MobiKwik (ikwik)', app: '📱' },
    { handle: '@cred.club', label: 'CRED', app: '📱' },
    { handle: '@credbank', label: 'CRED Bank', app: '📱' },
    { handle: '@tapicici', label: 'Tata Pay (ICICI)', app: '📱' },
    { handle: '@tapaxis', label: 'Tata Pay (Axis)', app: '📱' },
    { handle: '@superyes', label: 'SuperMoney', app: '📱' },
    { handle: '@jupiteraxis', label: 'Jupiter', app: '📱' },
    { handle: '@fiaxis', label: 'Fi Money', app: '📱' },
    { handle: '@sbiepay', label: 'SBI ePay', app: '🏦' },
    { handle: '@mahb', label: 'Bank of Maharashtra', app: '🏦' },
    { handle: '@barodampay', label: 'Baroda MPay', app: '🏦' },
    { handle: '@pockets', label: 'ICICI Pockets', app: '📱' },
    { handle: '@imobile', label: 'ICICI iMobile', app: '📱' },
    { handle: '@apaxis', label: 'Axis Pay', app: '📱' },
];

const upiSelectorStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=DM+Sans:wght@400;500&display=swap');

  .upi-wrap { position: relative; }

  .upi-name-row {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 10px;
  }

  .upi-name-input {
    flex: 1;
    padding: 13px 14px;
    border: 1.5px solid #e2ece2;
    border-radius: 13px;
    font-size: 14px;
    font-family: 'DM Sans', sans-serif;
    color: #1a2e1a;
    background: #f7f9f7;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .upi-name-input:focus {
    border-color: #3DB85C;
    box-shadow: 0 0 0 3px rgba(61,184,92,0.1);
    background: #fff;
  }

  .upi-at {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 20px;
    color: #3DB85C;
    flex-shrink: 0;
    padding: 0 2px;
  }

  .upi-handle-search {
    width: 100%;
    padding: 11px 14px 11px 36px;
    border: 1.5px solid #e2ece2;
    border-radius: 13px;
    font-size: 13.5px;
    font-family: 'DM Sans', sans-serif;
    color: #1a2e1a;
    background: #f7f9f7;
    outline: none;
    transition: border-color 0.2s;
    margin-bottom: 8px;
  }

  .upi-handle-search:focus {
    border-color: #3DB85C;
    background: #fff;
  }

  .upi-search-wrap {
    position: relative;
  }

  .upi-search-icon {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: #8a9e8a;
    font-size: 15px;
    pointer-events: none;
  }

  .upi-handle-list {
    max-height: 200px;
    overflow-y: auto;
    border: 1.5px solid #e2ece2;
    border-radius: 13px;
    background: #fff;
    margin-bottom: 10px;
  }

  .upi-handle-list::-webkit-scrollbar { width: 4px; }
  .upi-handle-list::-webkit-scrollbar-thumb { background: #c8dcc8; border-radius: 4px; }

  .upi-handle-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    cursor: pointer;
    transition: background 0.15s;
    border-bottom: 1px solid #f0f4f0;
    font-family: 'DM Sans', sans-serif;
  }

  .upi-handle-item:last-child { border-bottom: none; }

  .upi-handle-item:hover { background: #f3fbf5; }

  .upi-handle-item.selected {
    background: #e8f7ed;
    border-left: 3px solid #3DB85C;
  }

  .upi-handle-icon { font-size: 16px; flex-shrink: 0; }

  .upi-handle-text { flex: 1; }

  .upi-handle-name {
    font-size: 13px;
    color: #1a2e1a;
    font-weight: 500;
  }

  .upi-handle-tag {
    font-size: 11.5px;
    color: #6a8a6a;
    font-family: 'DM Sans', sans-serif;
  }

  .upi-handle-check {
    font-size: 14px;
    color: #3DB85C;
    font-weight: 900;
  }

  .upi-preview {
    background: #f3fbf5;
    border: 1.5px solid #b6dfc0;
    border-radius: 13px;
    padding: 12px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }

  .upi-preview-id {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    font-size: 15px;
    color: #1a4a1a;
    letter-spacing: 0.3px;
  }

  .upi-preview-badge {
    font-size: 11px;
    background: #3DB85C;
    color: #fff;
    border-radius: 7px;
    padding: 3px 9px;
    font-family: 'Nunito', sans-serif;
    font-weight: 700;
  }

  .upi-count-label {
    font-size: 11px;
    color: #8a9e8a;
    text-align: right;
    margin-bottom: 4px;
    font-family: 'DM Sans', sans-serif;
  }
`;

export function UpiSelector({ value, onChange }) {
    const [upiName, setUpiName] = React.useState('');
    const [selectedHandle, setSelectedHandle] = React.useState('');
    const [search, setSearch] = React.useState('');

    // Parse existing value if passed in
    React.useEffect(() => {
        if (value && value.includes('@')) {
            const [name, ...rest] = value.split('@');
            setUpiName(name);
            setSelectedHandle('@' + rest.join('@'));
        }
    }, []);

    const filtered = search.trim()
        ? UPI_HANDLES.filter(h =>
            h.handle.toLowerCase().includes(search.toLowerCase()) ||
            h.label.toLowerCase().includes(search.toLowerCase())
        )
        : UPI_HANDLES;

    function handleNameChange(e) {
        const name = e.target.value.replace(/[^a-zA-Z0-9._\-]/g, '');
        setUpiName(name);
        if (selectedHandle) {
            onChange(name + selectedHandle);
        }
    }

    function handleSelectHandle(handle) {
        setSelectedHandle(handle);
        if (upiName) onChange(upiName + handle);
        setSearch('');
    }

    const fullUpi = upiName && selectedHandle ? upiName + selectedHandle : '';
    const isValid = fullUpi && /^[\w.\-]{3,}@[\w]{3,}$/.test(fullUpi);

    return (
        <>
            <style>{upiSelectorStyles}</style>
            <div className="upi-wrap">

                {/* Name + @ row */}
                <div className="upi-name-row">
                    <input
                        className="upi-name-input"
                        placeholder="yourname"
                        value={upiName}
                        onChange={handleNameChange}
                        maxLength={40}
                    />
                    <span className="upi-at">@</span>
                </div>

                {/* Search handles */}
                <div className="upi-search-wrap">
                    <span className="upi-search-icon">🔍</span>
                    <input
                        className="upi-handle-search"
                        placeholder="Search bank or app (e.g. HDFC, PhonePe, Paytm...)"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                </div>

                <div className="upi-count-label">{filtered.length} handles available</div>

                {/* Handle list */}
                <div className="upi-handle-list">
                    {filtered.length === 0 && (
                        <div style={{ padding: '16px', textAlign: 'center', color: '#8a9e8a', fontSize: 13 }}>
                            No handles match "{search}"
                        </div>
                    )}
                    {filtered.map((h, i) => (
                        <div
                            key={i}
                            className={`upi-handle-item${selectedHandle === h.handle ? ' selected' : ''}`}
                            onClick={() => handleSelectHandle(h.handle)}
                        >
                            <span className="upi-handle-icon">{h.app}</span>
                            <div className="upi-handle-text">
                                <div className="upi-handle-name">{h.label}</div>
                                <div className="upi-handle-tag">{h.handle}</div>
                            </div>
                            {selectedHandle === h.handle && <span className="upi-handle-check">✓</span>}
                        </div>
                    ))}
                </div>

                {/* Live preview */}
                {fullUpi && (
                    <div className="upi-preview">
                        <span className="upi-preview-id">{fullUpi}</span>
                        {isValid
                            ? <span className="upi-preview-badge">✓ Valid</span>
                            : <span style={{ fontSize: 11, color: '#d97706', fontFamily: 'Nunito', fontWeight: 700 }}>⚠ Too short</span>
                        }
                    </div>
                )}
            </div>
        </>
    );
}