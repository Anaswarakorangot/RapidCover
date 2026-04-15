import { useState, useEffect, useRef } from 'react';

/**
 * RapidBot.jsx - Premium AI Assistant powered by Groq.
 * Custom Green & Glass styling for RapidCover.
 */

const S = `
  .bot-wrap {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #f7f9f7;
    background: linear-gradient(180deg, #ffffff 0%, #e8f7ed 100%);
    color: #1a2e1a;
    font-family: 'DM Sans', sans-serif;
  }
  
  .bot-header {
    padding: 20px;
    border-bottom: 1.5px solid #e2ece2;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(12px);
  }
  
  .bot-logo-wrap {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  
  .bot-logo {
    width: 34px;
    height: 34px;
    background: #3DB85C;
    color: #fff;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 18px;
    box-shadow: 0 0 15px rgba(61, 184, 92, 0.3);
  }
  
  .bot-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 17px;
    color: #1a2e1a;
  }
  
  .bot-badge {
    font-size: 10px;
    background: #e8f7ed;
    padding: 3px 8px;
    border-radius: 6px;
    color: #2a9e47;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 800;
    margin-left: 8px;
  }
  
  .bot-msgs {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }
  
  .bmsg {
    max-width: 85%;
    font-size: 14.5px;
    line-height: 1.6;
    animation: fadeIn 0.3s ease-out;
  }
  
  @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  
  .bmsg-user {
    align-self: flex-end;
    background: linear-gradient(135deg, #3DB85C, #2a9e47);
    padding: 12px 16px;
    border-radius: 18px 18px 4px 18px;
    color: #fff;
    box-shadow: 0 4px 12px rgba(61, 184, 92, 0.15);
  }
  
  .bmsg-bot {
    align-self: flex-start;
    display: flex;
    gap: 12px;
  }
  
  .bmsg-bot-avatar {
    width: 30px;
    height: 30px;
    background: #ffffff;
    color: #3DB85C;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 15px;
    flex-shrink: 0;
    border: 1.5px solid #e2ece2;
  }
  
  .bmsg-text {
    padding: 12px 16px;
    background: #ffffff;
    border: 1.5px solid #e2ece2;
    border-radius: 18px 18px 18px 4px;
    color: #4a5e4a;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03);
  }
  
  .bot-input-area {
    padding: 20px;
    background: #ffffff;
    border-top: 1.5px solid #e2ece2;
  }
  
  .bot-input-wrap {
    display: flex;
    gap: 12px;
    background: #f7f9f7;
    border: 1.5px solid #e2ece2;
    border-radius: 16px;
    padding: 6px;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  
  .bot-input-wrap:focus-within {
    border-color: #3DB85C;
    box-shadow: 0 0 0 4px rgba(61, 184, 92, 0.1);
    background: #ffffff;
  }
  
  .bot-input {
    flex: 1;
    background: transparent;
    border: none;
    padding: 10px 14px;
    color: #1a2e1a;
    font-size: 15px;
    outline: none;
    font-family: inherit;
  }
  
  .bot-send {
    background: #3DB85C;
    color: #fff;
    border: none;
    border-radius: 12px;
    width: 42px;
    height: 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 20px;
    transition: transform 0.2s, background 0.2s;
  }
  
  .bot-send:hover { background: #2a9e47; }
  .bot-send:active { transform: scale(0.92); }
  
  .bot-thinking {
    font-style: italic;
    color: #3DB85C;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .pulse {
    width: 6px; height: 6px; background: #3DB85C; border-radius: 50%;
    animation: pulse 1.5s infinite;
  }
  @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
  
  .bot-suggest {
    display: flex;
    gap: 10px;
    overflow-x: auto;
    padding: 0 20px 16px;
    scrollbar-width: none;
  }
  .bot-suggest::-webkit-scrollbar { display: none; }
  
  .bsug-pill {
    background: #ffffff;
    border: 1.5px solid #e2ece2;
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 12px;
    color: #4a5e4a;
    white-space: nowrap;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s;
    box-shadow: 0 2px 6px rgba(0,0,0,0.02);
  }
  
  .bsug-pill:hover {
    background: #e8f7ed;
    border-color: #3DB85C;
    color: #2a9e47;
  }
`;

export function RapidBot() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "RapidBot active. How can I help you regarding your policy, payouts, or eligibility today?" }
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const msgsEndRef = useRef(null);

  useEffect(() => {
    msgsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (textInput) => {
    const query = (textInput || input).trim();
    if (!query || isThinking) return;

    const newHistory = [...messages, { role: 'user', content: query }];
    setMessages(newHistory);
    setInput('');
    setIsThinking(true);

    try {
      const API_URL = import.meta.env.VITE_API_URL || '/api/v1';
      const res = await fetch(`${API_URL}/ai/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
        },
        body: JSON.stringify({ messages: newHistory })
      });
      
      if (!res.ok) throw new Error('RapidBot connection interrupted');
      
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Power grid disruption. My connection to the RapidCover network is unstable. Please retry."
      }]);
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className="bot-wrap">
      <style>{S}</style>
      
      <div className="bot-header">
        <div className="bot-logo-wrap">
          <div className="bot-logo">R</div>
          <div>
            <div className="bot-title">RapidBot <span className="bot-badge">Smart</span></div>
            <div style={{ fontSize: 10, color: '#3DB85C', opacity: 0.7, fontWeight: 700 }}>AI SUPPORT ENGINE</div>
          </div>
        </div>
      </div>
      
      <div className="bot-msgs">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'bmsg bmsg-user' : 'bmsg bmsg-bot'}>
            {m.role === 'assistant' && <div className="bmsg-bot-avatar">R</div>}
            <div className="bmsg-text">{m.content}</div>
          </div>
        ))}
        {isThinking && (
          <div className="bmsg bmsg-bot">
            <div className="bmsg-bot-avatar">R</div>
            <div className="bot-thinking">
              <span className="pulse" />
              RapidBot is thinking...
            </div>
          </div>
        )}
        <div ref={msgsEndRef} />
      </div>

      <div className="bot-suggest">
        {['7-day rule?', 'Rain payouts?', 'Is KYC safe?', 'Mumbai zones?'].map(s => (
          <div key={s} className="bsug-pill" onClick={() => handleSend(s)}>{s}</div>
        ))}
      </div>
      
      <div className="bot-input-area">
        <div className="bot-input-wrap">
          <input 
            className="bot-input" 
            placeholder="Ask RapidBot about your policy..." 
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
          />
          <button className="bot-send" onClick={() => handleSend()}>
            <span>↑</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default RapidBot;
