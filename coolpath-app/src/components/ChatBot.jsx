import { useState, useRef, useEffect } from 'react'
import { useLocation } from 'react-router-dom'

const API_BASE = 'http://localhost:8000'

// Simple markdown-lite renderer: bold **text**, newlines, bullet •
function renderMarkdown(text) {
  const lines = text.split('\n')
  return lines.map((line, i) => {
    // Replace **bold**
    const parts = line.split(/(\*\*[^*]+\*\*)/g).map((part, j) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={j}>{part.slice(2, -2)}</strong>
      }
      return part
    })
    return (
      <span key={i}>
        {parts}
        {i < lines.length - 1 && <br />}
      </span>
    )
  })
}

export default function ChatBot() {
  const location = useLocation()
  const isHome = location.pathname === '/'

  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        "Hi! I'm **EcoAssist** 🌿 — your AI guide for the CoolPath platform. Ask me about weather, tree canopy, cool routes, or anything about this platform!",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll to latest message
  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open, loading])

  // Focus input when opened
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 150)
  }, [open])

  async function sendMessage() {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { role: 'user', content: text }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const history = newMessages.slice(0, -1).map((m) => ({
        role: m.role,
        content: m.content,
      }))

      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Server error ${res.status}`)
      }

      const data = await res.json()
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
    } catch (err) {
      setError(err.message || 'Something went wrong. Is the backend running?')
      setMessages((prev) => prev.slice(0, -1)) // remove the user message on error
      setInput(text) // restore input
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (isHome) {
    return null
  }

  return (
    <>
      {/* ── Floating button ─────────────────────────────── */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? 'Close EcoAssist chat' : 'Open EcoAssist chat'}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 9999,
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #16a34a 0%, #15803d 50%, #0f5f2e 100%)',
          boxShadow: '0 4px 24px rgba(22,163,74,0.45), 0 2px 8px rgba(0,0,0,0.2)',
          transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.1)'
          e.currentTarget.style.boxShadow = '0 6px 32px rgba(22,163,74,0.6), 0 2px 8px rgba(0,0,0,0.25)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.boxShadow = '0 4px 24px rgba(22,163,74,0.45), 0 2px 8px rgba(0,0,0,0.2)'
        }}
      >
        {open ? (
          <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="white" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg width="26" height="26" viewBox="0 0 24 24" fill="white">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-4H7l5-8v4h4l-5 8z" />
          </svg>
        )}
      </button>

      {/* ── Chat panel ──────────────────────────────────── */}
      <div
        style={{
          position: 'fixed',
          bottom: '92px',
          right: '24px',
          zIndex: 9998,
          width: '380px',
          maxWidth: 'calc(100vw - 48px)',
          height: '520px',
          maxHeight: 'calc(100vh - 120px)',
          borderRadius: '20px',
          background: 'rgba(255,255,255,0.97)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          boxShadow: '0 24px 64px rgba(0,0,0,0.18), 0 4px 16px rgba(0,0,0,0.10)',
          border: '1px solid rgba(22,163,74,0.18)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          transformOrigin: 'bottom right',
          transition: 'opacity 0.22s ease, transform 0.22s ease',
          opacity: open ? 1 : 0,
          transform: open ? 'scale(1) translateY(0)' : 'scale(0.92) translateY(12px)',
          pointerEvents: open ? 'auto' : 'none',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            background: 'linear-gradient(135deg, #16a34a 0%, #15803d 100%)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px',
            }}
          >
            🌿
          </div>
          <div>
            <div style={{ color: 'white', fontWeight: '700', fontSize: '15px', lineHeight: 1.2 }}>
              EcoAssist
            </div>
            <div style={{ color: 'rgba(255,255,255,0.75)', fontSize: '11px', marginTop: '1px' }}>
              Powered by Llama 3 • CoolPath AI
            </div>
          </div>
          <div
            style={{
              marginLeft: 'auto',
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#86efac',
              boxShadow: '0 0 0 2px rgba(134,239,172,0.3)',
              animation: 'pulse 2s infinite',
            }}
          />
        </div>

        {/* Messages */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            scrollbarWidth: 'thin',
            scrollbarColor: '#d1fae5 transparent',
          }}
        >
          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                alignItems: 'flex-end',
                gap: '8px',
              }}
            >
              {msg.role === 'assistant' && (
                <div
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #16a34a, #15803d)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '14px',
                    flexShrink: 0,
                  }}
                >
                  🌿
                </div>
              )}
              <div
                style={{
                  maxWidth: '82%',
                  padding: '10px 14px',
                  borderRadius:
                    msg.role === 'user'
                      ? '18px 18px 4px 18px'
                      : '18px 18px 18px 4px',
                  background:
                    msg.role === 'user'
                      ? 'linear-gradient(135deg, #16a34a, #15803d)'
                      : '#f0fdf4',
                  color: msg.role === 'user' ? 'white' : '#14532d',
                  fontSize: '13.5px',
                  lineHeight: '1.55',
                  border: msg.role === 'assistant' ? '1px solid #bbf7d0' : 'none',
                  boxShadow:
                    msg.role === 'user'
                      ? '0 2px 8px rgba(22,163,74,0.3)'
                      : '0 1px 4px rgba(0,0,0,0.06)',
                }}
              >
                {renderMarkdown(msg.content)}
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {loading && (
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px' }}>
              <div
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #16a34a, #15803d)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '14px',
                  flexShrink: 0,
                }}
              >
                🌿
              </div>
              <div
                style={{
                  padding: '12px 16px',
                  borderRadius: '18px 18px 18px 4px',
                  background: '#f0fdf4',
                  border: '1px solid #bbf7d0',
                  display: 'flex',
                  gap: '4px',
                  alignItems: 'center',
                }}
              >
                {[0, 1, 2].map((dot) => (
                  <div
                    key={dot}
                    style={{
                      width: '7px',
                      height: '7px',
                      borderRadius: '50%',
                      background: '#16a34a',
                      animation: `typing-dot 1.2s ease-in-out ${dot * 0.2}s infinite`,
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div
              style={{
                padding: '10px 14px',
                borderRadius: '12px',
                background: '#fef2f2',
                border: '1px solid #fecaca',
                color: '#991b1b',
                fontSize: '12.5px',
              }}
            >
              ⚠️ {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input box */}
        <div
          style={{
            padding: '12px 16px',
            borderTop: '1px solid #dcfce7',
            background: 'rgba(240,253,244,0.6)',
            display: 'flex',
            gap: '8px',
            alignItems: 'flex-end',
            flexShrink: 0,
          }}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about weather, canopy, routes…"
            rows={1}
            style={{
              flex: 1,
              resize: 'none',
              border: '1.5px solid #bbf7d0',
              borderRadius: '12px',
              padding: '10px 14px',
              fontSize: '13.5px',
              fontFamily: 'inherit',
              outline: 'none',
              background: 'white',
              color: '#14532d',
              lineHeight: '1.45',
              maxHeight: '100px',
              overflowY: 'auto',
              transition: 'border-color 0.15s',
            }}
            onFocus={(e) => (e.target.style.borderColor = '#16a34a')}
            onBlur={(e) => (e.target.style.borderColor = '#bbf7d0')}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              border: 'none',
              cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
              background:
                loading || !input.trim()
                  ? '#d1fae5'
                  : 'linear-gradient(135deg, #16a34a, #15803d)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'background 0.15s, transform 0.1s',
              transform: 'scale(1)',
            }}
            onMouseEnter={(e) => {
              if (!loading && input.trim()) e.currentTarget.style.transform = 'scale(1.08)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)'
            }}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke={loading || !input.trim() ? '#86efac' : 'white'}
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>

      {/* Keyframe styles */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        @keyframes typing-dot {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30% { transform: translateY(-5px); opacity: 1; }
        }
      `}</style>
    </>
  )
}
