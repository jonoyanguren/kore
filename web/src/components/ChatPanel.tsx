import { useEffect, useRef, useState } from 'react'
import { apiChat, apiListMessages, type ChatMessage } from '../api'

type Props = {
  onAfterChat?: () => void
}

export function ChatPanel({ onAfterChat }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  async function load() {
    const rows = await apiListMessages()
    setMessages(rows.filter((m) => m.role === 'user' || m.role === 'assistant'))
  }

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        await load()
      } catch (e) {
        if (!cancelled) setError(String(e))
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  async function send() {
    const t = text.trim()
    if (!t || busy) return
    setText('')
    setBusy(true)
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: t }])
    try {
      const reply = await apiChat(t)
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
      onAfterChat?.()
    } catch (err) {
      setError(String(err))
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '(error al responder)' },
      ])
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="chat">
      <header className="chat__head">
        <h2>Chat</h2>
        <span className="muted">texto · mismo Jone que Telegram</span>
      </header>
      <div className="chat__log" aria-live="polite">
        {messages.length === 0 && !busy ? (
          <p className="muted chat__empty">Escribe algo para empezar…</p>
        ) : null}
        {messages.map((m, i) => (
          <div
            key={`${i}-${m.role}`}
            className={`chat__bubble chat__bubble--${m.role}`}
          >
            <span className="chat__who">
              {m.role === 'user' ? 'Tú' : 'Jone'}
            </span>
            <div className="chat__text">{m.content}</div>
          </div>
        ))}
        {busy ? <p className="muted chat__thinking">Pensando…</p> : null}
        <div ref={bottomRef} />
      </div>
      {error ? <p className="error">{error}</p> : null}
      <form
        className="chat__form"
        onSubmit={(e) => {
          e.preventDefault()
          void send()
        }}
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Mensaje…"
          rows={2}
          disabled={busy}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void send()
            }
          }}
        />
        <button type="submit" disabled={busy || !text.trim()}>
          Enviar
        </button>
      </form>
    </section>
  )
}
