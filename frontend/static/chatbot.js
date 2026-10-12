/**
 * chatbot.js – AI-powered chat assistant (OpenAI backend)
 */
(function () {
  let isOpen = false;
  let messages = [];

  const SYSTEM_MSG = `You are Events Booking Assistant, a helpful AI for the Events Booking platform — 
an event booking system for hackathons, workshops, and seminars. 
Help users find events, understand how to register, check their bookings, and navigate the platform.
Keep responses concise (2-3 sentences max). Be friendly and enthusiastic.`;

  function buildChatUI() {
    const wrapper = document.createElement('div');
    wrapper.id = 'chatbot-wrapper';
    wrapper.innerHTML = `
      <!-- Floating Trigger Button -->
      <button id="chatbot-trigger" aria-label="Open AI chat assistant" style="
        position:fixed; bottom:2rem; right:2rem; z-index:99990;
        width:58px; height:58px; border-radius:50%; border:none;
        background:linear-gradient(135deg,var(--primary,#00f2fe),var(--secondary,#ff0080));
        color:#0f172a; font-size:1.5rem; cursor:pointer;
        box-shadow:0 8px 25px rgba(0,242,254,0.4);
        display:flex; align-items:center; justify-content:center;
        transition:transform 0.3s ease, box-shadow 0.3s ease;
        animation: chatPulse 2.5s ease infinite;
      ">🤖</button>

      <!-- Chat Panel -->
      <div id="chatbot-panel" style="
        position:fixed; bottom:6.5rem; right:2rem; z-index:99991;
        width:340px; max-height:480px; border-radius:20px;
        background:var(--bg-card,rgba(15,23,42,0.97));
        border:1px solid var(--glass-border,rgba(255,255,255,0.12));
        box-shadow:0 20px 60px rgba(0,0,0,0.5);
        display:none; flex-direction:column; overflow:hidden;
        backdrop-filter:blur(16px);
        transform:translateY(20px) scale(0.97); opacity:0;
        transition:transform 0.35s cubic-bezier(0.34,1.56,0.64,1), opacity 0.3s ease;
        font-family:'Inter',sans-serif;
      ">
        <!-- Header -->
        <div style="
          padding:1rem 1.2rem; display:flex; align-items:center; gap:0.75rem;
          border-bottom:1px solid var(--glass-border,rgba(255,255,255,0.08));
          background:linear-gradient(135deg,rgba(0,242,254,0.08),rgba(255,0,128,0.05));
        ">
          <div style="
            width:36px;height:36px;border-radius:50%;
            background:linear-gradient(135deg,var(--primary,#00f2fe),var(--secondary,#ff0080));
            display:flex;align-items:center;justify-content:center;font-size:1.1rem;
          ">🤖</div>
          <div>
            <div style="font-weight:700;font-size:0.95rem;color:var(--text-main,#f1f5f9)">EVENTS AI</div>
            <div style="font-size:0.75rem;color:#10b981;display:flex;align-items:center;gap:4px">
              <span style="width:7px;height:7px;border-radius:50%;background:#10b981;display:inline-block"></span>
              Online
            </div>
          </div>
          <button id="chatbot-close" style="
            margin-left:auto;background:none;border:none;color:var(--text-muted,#94a3b8);
            font-size:1.3rem;cursor:pointer;line-height:1;padding:0.25rem;
          " aria-label="Close chat">&times;</button>
        </div>

        <!-- Messages -->
        <div id="chatbot-messages" style="
          flex:1;overflow-y:auto;padding:1rem;display:flex;flex-direction:column;gap:0.75rem;
          max-height:300px; scrollbar-width:thin;
        "></div>

        <!-- Input -->
        <div style="
          padding:0.85rem; border-top:1px solid var(--glass-border,rgba(255,255,255,0.08));
          display:flex; gap:0.5rem;
        ">
          <input id="chatbot-input" type="text" placeholder="Ask me anything..."
            aria-label="Chat message" style="
            flex:1; background:rgba(255,255,255,0.05); border:1px solid var(--glass-border,rgba(255,255,255,0.12));
            border-radius:50px; padding:0.6rem 1rem; color:var(--text-main,#f1f5f9);
            font-size:0.88rem; outline:none; font-family:inherit;
            transition:border-color 0.2s;
          ">
          <button id="chatbot-send" aria-label="Send message" style="
            background:var(--primary,#00f2fe); border:none; border-radius:50%;
            width:38px;height:38px; display:flex;align-items:center;justify-content:center;
            cursor:pointer; font-size:1rem; flex-shrink:0; color:#0f172a; transition:0.2s;
          ">➤</button>
        </div>
      </div>
    `;

    // CSS for pulse animation
    const style = document.createElement('style');
    style.textContent = `
      @keyframes chatPulse {
        0%,100% { box-shadow: 0 8px 25px rgba(0,242,254,0.4); }
        50%      { box-shadow: 0 8px 35px rgba(0,242,254,0.7), 0 0 0 8px rgba(0,242,254,0.1); }
      }
      #chatbot-panel::-webkit-scrollbar { width: 4px; }
      #chatbot-panel::-webkit-scrollbar-track { background: transparent; }
      #chatbot-panel::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
      #chatbot-messages::-webkit-scrollbar { width: 3px; }
      #chatbot-messages::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); }

      @media (max-width: 600px) {
        #chatbot-trigger {
          bottom: 1.2rem !important;
          right: 1.2rem !important;
          width: 50px !important;
          height: 50px !important;
          font-size: 1.3rem !important;
        }
        #chatbot-panel {
          bottom: 4.8rem !important;
          right: 12px !important;
          left: 12px !important;
          width: auto !important;
          max-width: calc(100vw - 24px) !important;
          max-height: min(480px, calc(100vh - 100px)) !important;
          border-radius: 16px !important;
        }
        #chatbot-messages {
          max-height: calc(100vh - 230px) !important;
        }
      }
    `;
    document.head.appendChild(style);
    document.body.appendChild(wrapper);

    // Wire up events
    document.getElementById('chatbot-trigger').addEventListener('click', toggleChat);
    document.getElementById('chatbot-close').addEventListener('click', closeChat);
    document.getElementById('chatbot-send').addEventListener('click', sendMessage);
    document.getElementById('chatbot-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendMessage();
    });

    // Show welcome message
    addMessage('assistant', "Hi! I'm your EVENTS AI assistant 👋 Ask me about events, how to register, or anything else!");
  }

  function toggleChat() {
    isOpen ? closeChat() : openChat();
  }

  function openChat() {
    isOpen = true;
    const panel = document.getElementById('chatbot-panel');
    panel.style.display = 'flex';
    requestAnimationFrame(() => {
      panel.style.transform = 'translateY(0) scale(1)';
      panel.style.opacity = '1';
    });
    document.getElementById('chatbot-input').focus();
  }

  function closeChat() {
    isOpen = false;
    const panel = document.getElementById('chatbot-panel');
    panel.style.transform = 'translateY(20px) scale(0.97)';
    panel.style.opacity = '0';
    setTimeout(() => { panel.style.display = 'none'; }, 320);
  }

  function addMessage(role, text) {
    const container = document.getElementById('chatbot-messages');
    const isUser = role === 'user';
    const div = document.createElement('div');
    div.style.cssText = `
      display:flex; justify-content:${isUser ? 'flex-end' : 'flex-start'};
    `;
    div.innerHTML = `
      <div style="
        max-width:80%; padding:0.65rem 0.9rem; border-radius:${isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px'};
        background:${isUser ? 'linear-gradient(135deg,var(--primary,#00f2fe),rgba(0,180,220,0.8))' : 'rgba(255,255,255,0.07)'};
        color:${isUser ? '#0f172a' : 'var(--text-main,#f1f5f9)'};
        font-size:0.87rem; line-height:1.5; font-weight:${isUser ? '600' : '400'};
      ">${text}</div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    messages.push({ role, content: text });
  }

  function addTypingIndicator() {
    const container = document.getElementById('chatbot-messages');
    const div = document.createElement('div');
    div.id = 'chatbot-typing';
    div.style.cssText = 'display:flex; justify-content:flex-start;';
    div.innerHTML = `
      <div style="
        padding:0.65rem 0.9rem; border-radius:16px 16px 16px 4px;
        background:rgba(255,255,255,0.07); display:flex; gap:4px; align-items:center;
      ">
        ${[0,150,300].map(d => `<span style="
          width:6px;height:6px;border-radius:50%;background:var(--text-muted,#94a3b8);
          animation:typingDot 1s ease ${d}ms infinite;display:inline-block;
        "></span>`).join('')}
      </div>
    `;
    if (!document.getElementById('typing-style')) {
      const s = document.createElement('style');
      s.id = 'typing-style';
      s.textContent = `@keyframes typingDot { 0%,100%{opacity:0.3;transform:translateY(0)} 50%{opacity:1;transform:translateY(-3px)} }`;
      document.head.appendChild(s);
    }
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  function removeTypingIndicator() {
    const t = document.getElementById('chatbot-typing');
    if (t) t.remove();
  }

  async function sendMessage() {
    const input = document.getElementById('chatbot-input');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    addMessage('user', text);
    addTypingIndicator();

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: messages.slice(-6) }),
      });
      const data = await resp.json();
      removeTypingIndicator();
      addMessage('assistant', data.reply || 'Sorry, I had trouble responding. Please try again.');
    } catch {
      removeTypingIndicator();
      addMessage('assistant', 'Connection issue. Please check your internet and try again.');
    }
  }

  document.addEventListener('DOMContentLoaded', buildChatUI);
})();
