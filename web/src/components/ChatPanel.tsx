import { useEffect, useRef, useState } from 'react'
import {
  apiChat,
  apiCompleteTask,
  apiListMessages,
  type ChatMessage,
} from '../api'
import { formatRelativeEs } from '../relativeTime'
import type { Task } from '../types'
import { ChatTaskCard } from './ChatTaskCard'

type Props = {
  onAfterChat?: (info: { tasksChanged: boolean }) => void
}

const QUICK: { label: string; send: string }[] = [
  { label: '/tareas', send: '/tareas' },
  { label: '/hora', send: '/hora' },
  { label: '/agenda', send: '/agenda' },
  { label: '/diario', send: '/diario' },
  { label: '/dream', send: '/dream' },
]

function looksLikeTaskClaim(text: string): boolean {
  return /\b(cread|añadid|agregad|apuntd)\b/i.test(text)
}

function dedupeTasks(tasks: Task[]): Task[] {
  const seen = new Set<number>()
  const out: Task[] = []
  for (const t of tasks) {
    if (seen.has(t.id)) continue
    seen.add(t.id)
    out.push(t)
  }
  return out
}

function whenLabel(m: ChatMessage, now: Date): string {
  if (m.created_at) return formatRelativeEs(m.created_at, now)
  return m.relative ?? ''
}

export function ChatPanel({ onAfterChat }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const bottomRef = useRef<HTMLDivElement>(null)

  async function load() {
    const rows = await apiListMessages(100)
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

  // Re-render relative labels every minute
  useEffect(() => {
    const id = window.setInterval(() => setTick((n) => n + 1), 60_000)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy, tick])

  async function sendText(raw: string) {
    const t = raw.trim()
    if (!t || busy) return
    setText('')
    setBusy(true)
    setError(null)
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: t, relative: 'hace un momento', tasks: [] },
    ])
    try {
      const result = await apiChat(t)
      let reply = result.reply
      if (
        looksLikeTaskClaim(reply) &&
        result.tasks_created.length === 0 &&
        !result.tasks_changed &&
        !t.startsWith('/')
      ) {
        reply +=
          '\n\n(Ojo: no quedó registrada en SQLite — la tool no corrió. Prueba otra vez o añádela en el board.)'
      }
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: reply,
          relative: 'hace un momento',
          tasks: dedupeTasks(result.tasks_listed),
        },
      ])
      try {
        await load()
      } catch {
        /* keep optimistic */
      }
      onAfterChat?.({
        tasksChanged: result.tasks_changed || result.tasks_listed.length > 0,
      })
    } catch (err) {
      setError(String(err))
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '(error al responder)', tasks: [] },
      ])
    } finally {
      setBusy(false)
    }
  }

  async function onCompleteTask(id: number) {
    try {
      await apiCompleteTask(id)
      await load()
      onAfterChat?.({ tasksChanged: true })
    } catch (e) {
      setError(String(e))
    }
  }

  const now = new Date()
  // tick forces recompute of relative labels
  void tick

  return (
    <section className="chat">
      <header className="chat__head">
        <h2>Chat</h2>
        <span className="muted">últimos 100 · Jone</span>
      </header>
      <div className="chat__quick" aria-label="Acciones rápidas">
        {QUICK.map((q) => (
          <button
            key={q.send}
            type="button"
            className="chat__chip"
            disabled={busy}
            onClick={() => void sendText(q.send)}
          >
            {q.label}
          </button>
        ))}
      </div>
      <div className="chat__log" aria-live="polite">
        {messages.length === 0 && !busy ? (
          <p className="muted chat__empty">Escribe algo o pulsa /tareas…</p>
        ) : null}
        {messages.map((m, i) => (
          <div
            key={m.id ?? `${i}-${m.role}`}
            className={`chat__bubble chat__bubble--${m.role}`}
          >
            <div className="chat__meta">
              <span className="chat__who">
                {m.role === 'user' ? 'Tú' : 'Jone'}
              </span>
              {whenLabel(m, now) ? (
                <time className="chat__when" dateTime={m.created_at}>
                  {whenLabel(m, now)}
                </time>
              ) : null}
            </div>
            <div className="chat__text">{m.content}</div>
            {m.tasks && m.tasks.length > 0 ? (
              <div className="chat__tasks">
                {m.tasks.map((task) => (
                  <ChatTaskCard
                    key={task.id}
                    task={task}
                    onComplete={onCompleteTask}
                  />
                ))}
              </div>
            ) : null}
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
          void sendText(text)
        }}
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Mensaje o /tareas…"
          rows={2}
          disabled={busy}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void sendText(text)
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
