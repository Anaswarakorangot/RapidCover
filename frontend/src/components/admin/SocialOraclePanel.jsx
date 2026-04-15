import React, { useState, useRef, useEffect } from 'react';
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const styles = `
  .oracle-wrap {
    background: #fff;
    border: 1px solid #e2ece2;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    font-family: -apple-system, system-ui, sans-serif;
  }
  .oracle-header {
    display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;
  }
  .oracle-title { font-weight: 700; font-size: 16px; color: #1a2e1a; display: flex; align-items: center; gap: 8px;}
  .oracle-badge {
    background: #e0e7ff; color: #4338ca; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
  }
  .oracle-badge-live {
    background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
    animation: pulse-green 2s infinite;
  }
  @keyframes pulse-green {
    0%, 100% { box-shadow: 0 0 0 0 rgba(22,163,74,0.3); }
    50% { box-shadow: 0 0 0 6px rgba(22,163,74,0); }
  }
  .oracle-desc { font-size: 13px; color: #4a5e4a; margin-bottom: 16px; line-height: 1.5; }
  .oracle-input-area {
    width: 100%; height: 100px; padding: 12px; border: 1.5px solid #d1d5db; border-radius: 8px; font-size: 14px; font-family: monospace; resize: none; margin-bottom: 12px; outline: none; transition: border-color 0.2s; box-sizing: border-box;
  }
  .oracle-input-area:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
  .oracle-btn {
    background: linear-gradient(135deg, #4f46e5, #4338ca); color: #fff; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: transform 0.1s, opacity 0.2s; display: flex; align-items: center; gap: 8px;
  }
  .oracle-btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .oracle-btn:active:not(:disabled) { transform: scale(0.98); }
  
  .oracle-terminal {
    background: #0f172a; color: #2dd4bf; font-family: 'Courier New', Courier, monospace; font-size: 13px; padding: 16px; border-radius: 8px; min-height: 180px; max-height: 320px; overflow-y: auto; margin-top: 16px; box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
  }
  .oracle-log-line { margin-bottom: 6px; line-height: 1.4; }
  .oracle-log-agent { color: #a78bfa; }
  .oracle-log-security { color: #fbbf24; }
  .oracle-log-oracle { color: #2dd4bf; }
  .oracle-log-decision { color: #a3e635; font-weight: bold; }
  .oracle-log-error { color: #ef4444; font-weight: bold; }
  .oracle-log-done { color: #38bdf8; font-weight: bold; }
  .blinking-cursor { animation: blink 1s step-end infinite; }
  @keyframes blink { 50% { opacity: 0; } }

  .oracle-verdict {
    margin-top: 16px; padding: 14px 16px; border-radius: 10px; font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 10px;
  }
  .oracle-verdict.verified {
    background: linear-gradient(135deg, #dcfce7, #bbf7d0); color: #166534; border: 1px solid #86efac;
  }
  .oracle-verdict.rejected {
    background: linear-gradient(135deg, #fee2e2, #fecaca); color: #991b1b; border: 1px solid #fca5a5;
  }
  .oracle-verdict.inconclusive {
    background: linear-gradient(135deg, #fef9c3, #fde68a); color: #92400e; border: 1px solid #fcd34d;
  }
  .oracle-confidence-bar {
    margin-top: 12px; height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden;
  }
  .oracle-confidence-fill {
    height: 100%; border-radius: 4px; transition: width 1s ease-out;
  }
  .oracle-samples {
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;
  }
  .oracle-sample-btn {
    background: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 6px;
    font-size: 12px; cursor: pointer; transition: all 0.2s; color: #475569;
  }
  .oracle-sample-btn:hover {
    background: #e0e7ff; border-color: #818cf8; color: #4338ca;
  }
`;

const SAMPLE_POSTS = [
  // ── WILL VERIFY ✅ (matches real current conditions) ──
  { label: "✅ Mumbai AQI", text: "Andheri East air quality has gotten really bad today. My eyes are burning and I can barely see across the road. Multiple riders in our Blinkit hub are complaining of headaches and breathing issues. Hub manager said we can log off early if needed. Is anyone else facing this? #MumbaiAir #DeliveryRiders" },
  { label: "✅ Delhi Smog", text: "yaar CP area mein aaj saans lena mushkil ho raha hai 😷 haze itna thick hai ki traffic signals bhi dhang se nahi dikh rahe. mere 2 deliveries cancel ho gayi because customers said dont come out in this pollution. AQI bahut kharab lag raha hai. any other riders facing this near connaught place? #DelhiPollution" },
  { label: "✅ Mumbai Haze", text: "Just stepped out for deliveries near Andheri station and the smog is unreal today. Can smell something burning in the air. My throat started hurting within 10 minutes. Other Zepto riders are wearing masks but it's still difficult. Requesting platform to check air quality before sending us out 🙏" },
  // ── WILL REJECT ❌ (fake / conditions don't match reality) ──
  { label: "❌ Fake Rain BLR", text: "OMG Koramangala is completely flooded right now!! 🌊 Water everywhere, roads are like rivers, my bike is submerged!! Worst rainfall in 100 years!! All deliveries impossible!! #BangaloreFloods #Emergency" },
  { label: "❌ Subtle Fake", text: "Just saw on TV that Indiranagar is completely flooded!! Roads submerged waist-level!! 😱 But also I'm sitting at a cafe in Indiranagar right now and it's actually sunny and beautiful today lol. Still, SHARE THIS so delivery companies suspend work!! RT for awareness 🙏" },
  { label: "❌ Snow Hoax", text: "BREAKING NEWS!! 50 feet of snow has fallen in Electronic City Bangalore!! Temperature dropped to -20°C!! All the pothole puddles have turned into glacier lakes!! Riders are using boats instead of bikes!! This is totally NOT satire!! 🚣‍♂️🏔️ #BangaloreWeather" },
  { label: "❌ Vague Copy", text: "A friend told me that someone posted that there might be flooding somewhere in some city in India. I haven't verified this myself and I'm actually in London right now but please share this important weather update for our delivery workers. Stay safe everyone! 🌍" },
];

export default function SocialOraclePanel() {
  const [text, setText] = useState(SAMPLE_POSTS[0].text);
  const [analyzing, setAnalyzing] = useState(false);
  const [logs, setLogs] = useState([]);
  const [verdict, setVerdict] = useState(null);
  const terminalRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const handleAnalyze = async () => {
    if (!text.trim() || analyzing) return;
    setAnalyzing(true);
    setLogs([]);
    setVerdict(null);

    try {
      const res = await fetch(`${API_BASE}/admin/panel/social-oracle/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim() }),
      });

      if (!res.ok) {
        throw new Error(`Backend returned ${res.status}`);
      }

      // Stream NDJSON response line by line
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete line in buffer

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const parsed = JSON.parse(line);
            if (parsed.type === 'done') {
              setVerdict(parsed);
            } else {
              setLogs(prev => [...prev, { msg: parsed.msg, type: parsed.type }]);
            }
          } catch {
            // Skip unparseable lines
          }
        }
      }

      // Process any remaining buffer
      if (buffer.trim()) {
        try {
          const parsed = JSON.parse(buffer);
          if (parsed.type === 'done') {
            setVerdict(parsed);
          } else {
            setLogs(prev => [...prev, { msg: parsed.msg, type: parsed.type }]);
          }
        } catch {
          // Failed to parse buffer
        }
      }

      // If verified, fire the actual trigger
      if (verdict === null) {
        // Wait a tick for state to update, then check via the parsed data
      }

    } catch (err) {
      setLogs(prev => [...prev, { msg: `PIPELINE ERROR: ${err.message}`, type: 'error' }]);
    } finally {
      setAnalyzing(false);
    }
  };

  // Fire trigger if verdict comes back verified
  useEffect(() => {
    if (verdict && verdict.verified && verdict.zone_code && verdict.trigger_type) {
      const fireTrigger = async () => {
        setLogs(prev => [...prev, {
          msg: `Dispatching POST /api/v1/admin/panel/simulate-trigger for zone ${verdict.zone_code}...`,
          type: 'agent'
        }]);

        try {
          const res = await fetch(`${API_BASE}/admin/panel/simulate-trigger`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              triggerType: verdict.trigger_type,
              zone: verdict.zone_code,
            }),
          });

          if (res.ok) {
            setLogs(prev => [...prev, {
              msg: `SUCCESS: Smart Contract executed. Payouts disbursed to ${verdict.zone_code} pool. ✓`,
              type: 'decision'
            }]);
          } else {
            setLogs(prev => [...prev, {
              msg: `Trigger dispatched but backend returned ${res.status}. Check admin logs.`,
              type: 'security'
            }]);
          }
        } catch (err) {
          setLogs(prev => [...prev, {
            msg: `Trigger dispatch failed: ${err.message}`,
            type: 'error'
          }]);
        }
      };
      fireTrigger();
    }
  }, [verdict]);

  const getVerdictClass = () => {
    if (!verdict) return '';
    if (verdict.verified) return 'verified';
    if (verdict.confidence >= 40) return 'inconclusive';
    return 'rejected';
  };

  const getConfidenceColor = () => {
    if (!verdict) return '#64748b';
    if (verdict.confidence >= 70) return '#22c55e';
    if (verdict.confidence >= 40) return '#eab308';
    return '#ef4444';
  };

  return (
    <>
      <style>{styles}</style>
      <div className="oracle-wrap">
        <div className="oracle-header">
          <div className="oracle-title">
            🔮 LLM Social Oracle Verification
            <span className="oracle-badge">Agentic Workflow</span>
            <span className="oracle-badge-live">GPS + API</span>
          </div>
        </div>
        
        <p className="oracle-desc">
          Verify social media posts against <strong>real-world data</strong>. Paste any tweet, WhatsApp forward, or report.
          The oracle extracts the location (GPS), queries live weather/AQI APIs, cross-validates conditions,
          and autonomously triggers payouts if confidence ≥ 70%.
        </p>

        <div className="oracle-samples">
          {SAMPLE_POSTS.map((sample, i) => (
            <button
              key={i}
              className="oracle-sample-btn"
              onClick={() => setText(sample.text)}
              disabled={analyzing}
            >
              {sample.label}
            </button>
          ))}
        </div>

        <textarea 
          className="oracle-input-area"
          value={text}
          onChange={e => setText(e.target.value)}
          disabled={analyzing}
          placeholder="Paste raw social media report here..."
        />
        
        <button className="oracle-btn" onClick={handleAnalyze} disabled={analyzing || !text.trim()}>
          {analyzing ? '⚙️ Oracle is verifying...' : '🧠 Verify & Trigger Payout'}
        </button>

        <div className="oracle-terminal" ref={terminalRef}>
          {logs.length === 0 && !analyzing && <span style={{ color: '#64748b' }}>Awaiting social media payload for verification...</span>}
          {logs.map((log, i) => (
            <div key={i} className="oracle-log-line">
              <span className={`oracle-log-${log.type}`}>[{log.type.toUpperCase()}]</span> {log.msg}
            </div>
          ))}
          {analyzing && <div className="oracle-log-line">_ <span className="blinking-cursor">█</span></div>}
        </div>

        {verdict && (
          <>
            <div className="oracle-confidence-bar">
              <div
                className="oracle-confidence-fill"
                style={{
                  width: `${verdict.confidence}%`,
                  background: `linear-gradient(90deg, ${getConfidenceColor()}, ${getConfidenceColor()}aa)`,
                }}
              />
            </div>
            <div className={`oracle-verdict ${getVerdictClass()}`}>
              {verdict.verified ? '✅' : verdict.confidence >= 40 ? '⚠️' : '❌'}
              {' '}{verdict.msg}
              <span style={{ marginLeft: 'auto', fontSize: 13, opacity: 0.8 }}>
                {verdict.confidence}%
              </span>
            </div>
          </>
        )}
      </div>
    </>
  );
}
