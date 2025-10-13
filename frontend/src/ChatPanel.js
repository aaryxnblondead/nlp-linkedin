import React, { useEffect, useMemo, useRef, useState } from 'react';
import { chatApplicant } from './api/apiClient';
import './index.css';

export default function ChatPanel({ token, onClose }){
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! Ask me about your talent corpus. I answer from indexed resumes and insights.' }
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const listRef = useRef(null);

  useEffect(() => {
    if(listRef.current){
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  const canSend = useMemo(() => input.trim().length > 0 && !busy, [input, busy]);

  const send = async () => {
    if(!canSend) return;
    const userMsg = { role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setBusy(true);
    try{
      const res = await chatApplicant(undefined, [...messages, userMsg], token, { top_k: 8, max_new_tokens: 256 });
      const reply = (res.data && res.data.reply) ? String(res.data.reply) : "I couldn't find enough information to answer that.";
      setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    }catch(err){
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry — I'm having trouble right now." }]);
    }finally{
      setBusy(false);
    }
  };

  const onKeyDown = (e) => {
    if(e.key === 'Enter' && !e.shiftKey){
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="chat-dock">
      <div className="chat-header">
        <div>
          <div className="chat-title">Assistant</div>
          <div className="chat-sub">Grounded in your corpus</div>
        </div>
        <button className="btn btn-sm btn-secondary" onClick={onClose}>Close</button>
      </div>
      <div className="chat-list" ref={listRef}>
        {messages.map((m, idx) => (
          <div key={idx} className={`chat-msg ${m.role === 'user' ? 'me' : 'bot'}`}>
            <div className="chat-bubble">{m.content}</div>
          </div>
        ))}
      </div>
      <div className="chat-input">
        <textarea
          className="textarea"
          placeholder="Ask about experience, skills, projects across your corpus…"
          rows={2}
          value={input}
          onChange={(e)=>setInput(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button className="btn" onClick={send} disabled={!canSend}>{busy ? 'Thinking…' : 'Send'}</button>
      </div>
    </div>
  );
}
