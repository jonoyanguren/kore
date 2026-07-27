import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
  useState,
} from 'react'
import {
  apiChatLive,
  apiCompleteTask,
  apiListMessages,
  apiPatchTask,
  apiTranscribe,
  type ChatMessage,
} from '../api'
import { formatRelativeEs } from '../relativeTime'
import type { SpaceId } from '../spaces'
import { spaceDef } from '../spaces'
import type { Task } from '../types'
import { ChatTaskCard } from './ChatTaskCard'
import { useToast } from './Toasts'

export type ChatPanelHandle = {
  run: (text: string) => void
}

type Props = {
  onAfterChat?: (info: { tasksChanged: boolean }) => void
  onOpenTask?: (task: Task) => void
  space?: SpaceId
}

const PAGE = 10
const TOP_LOAD_PX = 72
const BOTTOM_STICK_PX = 80

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

function patchTasksInMessages(
  messages: ChatMessage[],
  id: number,
  patch: Partial<Task>,
): ChatMessage[] {
  return messages.map((m) => {
    if (!m.tasks?.length) return m
    return {
      ...m,
      tasks: m.tasks.map((t) => (t.id === id ? { ...t, ...patch } : t)),
    }
  })
}

function firstPersistedId(messages: ChatMessage[]): number | undefined {
  for (const m of messages) {
    if (typeof m.id === 'number') return m.id
  }
  return undefined
}

type MicState = 'idle' | 'recording' | 'transcribing'

export const ChatPanel = forwardRef<ChatPanelHandle, Props>(function ChatPanel(
  { onAfterChat, onOpenTask, space = 'all' },
  ref,
) {
  const toast = useToast()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const telegramTipShown = useRef(false)
  const [hasMore, setHasMore] = useState(false)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [thinking, setThinking] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const [mic, setMic] = useState<MicState>('idle')
  const [levels, setLevels] = useState<number[]>(() => Array(28).fill(0.08))
  const [recSecs, setRecSecs] = useState(0)
  const bottomRef = useRef<HTMLDivElement>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const busyRef = useRef(false)
  const stickBottomRef = useRef(true)
  const loadingOlderRef = useRef(false)
  const skipStickOnceRef = useRef(false)
  const mediaRecRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<BlobPart[]>([])
  const audioCtxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const rafRef = useRef<number>(0)
  const recStartedAtRef = useRef(0)
  const spaceProject = spaceDef(space).project

  useEffect(() => {
    busyRef.current = busy
  }, [busy])

  const stopMeter = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = 0
    }
    analyserRef.current = null
    const ctx = audioCtxRef.current
    audioCtxRef.current = null
    if (ctx) {
      void ctx.close().catch(() => undefined)
    }
    setLevels(Array(28).fill(0.08))
    setRecSecs(0)
  }, [])

  const startMeter = useCallback((stream: MediaStream) => {
    stopMeter()
    const AC =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext })
        .webkitAudioContext
    const ctx = new AC()
    const source = ctx.createMediaStreamSource(stream)
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 64
    analyser.smoothingTimeConstant = 0.72
    source.connect(analyser)
    audioCtxRef.current = ctx
    analyserRef.current = analyser
    recStartedAtRef.current = Date.now()
    const data = new Uint8Array(analyser.frequencyBinCount)

    const tickMeter = () => {
      const a = analyserRef.current
      if (!a) return
      a.getByteFrequencyData(data)
      const bars = 28
      const step = Math.max(1, Math.floor(data.length / bars))
      const next: number[] = []
      for (let i = 0; i < bars; i++) {
        let sum = 0
        for (let j = 0; j < step; j++) sum += data[i * step + j] ?? 0
        const v = sum / step / 255
        next.push(Math.max(0.06, Math.min(1, v * 1.35)))
      }
      setLevels(next)
      setRecSecs(Math.floor((Date.now() - recStartedAtRef.current) / 1000))
      rafRef.current = requestAnimationFrame(tickMeter)
    }
    rafRef.current = requestAnimationFrame(tickMeter)
  }, [stopMeter])

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'auto') => {
    const log = logRef.current
    if (!log) return
    log.scrollTo({ top: log.scrollHeight, behavior })
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const page = await apiListMessages(PAGE)
        if (cancelled) return
        setMessages(page.messages)
        setHasMore(page.has_more)
        stickBottomRef.current = true
      } catch (e) {
        if (!cancelled) setError(String(e))
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const id = window.setInterval(() => setTick((n) => n + 1), 30_000)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    return () => {
      const rec = mediaRecRef.current
      if (rec && rec.state !== 'inactive') {
        try {
          rec.stop()
        } catch {
          /* ignore */
        }
      }
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      const ctx = audioCtxRef.current
      if (ctx) void ctx.close().catch(() => undefined)
    }
  }, [])

  useLayoutEffect(() => {
    if (skipStickOnceRef.current) {
      skipStickOnceRef.current = false
      return
    }
    if (stickBottomRef.current) {
      scrollToBottom('auto')
    }
  }, [messages, busy, thinking, scrollToBottom])

  const loadOlder = useCallback(async () => {
    if (loadingOlderRef.current || !hasMore) return
    const before = firstPersistedId(messages)
    if (before == null) return
    const log = logRef.current
    const prevHeight = log?.scrollHeight ?? 0
    const prevTop = log?.scrollTop ?? 0
    loadingOlderRef.current = true
    setLoadingOlder(true)
    try {
      const page = await apiListMessages(PAGE, before)
      skipStickOnceRef.current = true
      setMessages((prev) => {
        const seen = new Set(prev.map((m) => m.id).filter(Boolean))
        const older = page.messages.filter((m) => m.id && !seen.has(m.id))
        return [...older, ...prev]
      })
      setHasMore(page.has_more)
      requestAnimationFrame(() => {
        const el = logRef.current
        if (!el) return
        el.scrollTop = el.scrollHeight - prevHeight + prevTop
      })
    } catch (e) {
      setError(String(e))
    } finally {
      loadingOlderRef.current = false
      setLoadingOlder(false)
    }
  }, [hasMore, messages])

  function onLogScroll() {
    const log = logRef.current
    if (!log) return
    const distBottom = log.scrollHeight - log.scrollTop - log.clientHeight
    stickBottomRef.current = distBottom < BOTTOM_STICK_PX
    if (log.scrollTop < TOP_LOAD_PX) {
      void loadOlder()
    }
  }

  async function sendText(raw: string) {
    const t = raw.trim()
    if (!t || busyRef.current) return
    setText('')
    setBusy(true)
    stickBottomRef.current = true
    setThinking(t.startsWith('/') ? 'Ejecutando…' : 'Pensando…')
    setError(null)
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: t, relative: 'hace un momento', tasks: [] },
    ])
    try {
      const result = await apiChatLive(
        t,
        {
          onStatus: (label) => {
            stickBottomRef.current = true
            setThinking(label)
          },
        },
        spaceProject,
      )
      setThinking(null)
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
      stickBottomRef.current = true
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
        const page = await apiListMessages(PAGE)
        setMessages((prev) => {
          const firstNew = page.messages[0]?.id
          if (firstNew == null) return prev
          const older = prev.filter(
            (m) => typeof m.id === 'number' && m.id < firstNew,
          )
          return [...older, ...page.messages]
        })
        setHasMore(page.has_more)
      } catch {
        /* keep optimistic */
      }
      stickBottomRef.current = true
      requestAnimationFrame(() => scrollToBottom('smooth'))
      if (result.tasks_changed || result.tasks_created.length > 0) {
        toast.ok('Tareas actualizadas')
        if (!telegramTipShown.current) {
          telegramTipShown.current = true
          toast.info('Mismo vault que Telegram — ya está sync')
        }
      }
      onAfterChat?.({
        tasksChanged: result.tasks_changed || result.tasks_listed.length > 0,
      })
    } catch (err) {
      setThinking(null)
      const msg = String(err)
      setError(msg)
      toast.err(msg.includes('abort') ? 'El modelo tardó demasiado' : msg)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '(error al responder)', tasks: [] },
      ])
    } finally {
      setBusy(false)
      setThinking(null)
      stickBottomRef.current = true
      requestAnimationFrame(() => scrollToBottom('smooth'))
    }
  }

  useImperativeHandle(ref, () => ({
    run: (cmd: string) => {
      void sendText(cmd)
    },
  }))

  async function finishRecording(blob: Blob) {
    stopMeter()
    setMic('transcribing')
    try {
      const transcribed = await apiTranscribe(blob)
      if (!transcribed) {
        toast.err('No se oyó nada')
        return
      }
      setText((prev) => (prev.trim() ? `${prev.trim()} ${transcribed}` : transcribed))
      toast.ok('Transcrito — edita o Envía')
    } catch (e) {
      const msg = String(e)
      setError(msg)
      toast.err(msg.includes('abort') ? 'Transcripción lenta' : msg)
    } finally {
      setMic('idle')
    }
  }

  async function toggleMic() {
    if (busy || mic === 'transcribing') return
    if (mic === 'recording') {
      const rec = mediaRecRef.current
      if (rec && rec.state !== 'inactive') rec.stop()
      return
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      toast.err('Micrófono no disponible en este navegador')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : ''
      const rec = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream)
      chunksRef.current = []
      mediaRecRef.current = rec
      rec.ondataavailable = (ev) => {
        if (ev.data.size > 0) chunksRef.current.push(ev.data)
      }
      rec.onstop = () => {
        stopMeter()
        stream.getTracks().forEach((t) => t.stop())
        const type = rec.mimeType || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type })
        chunksRef.current = []
        mediaRecRef.current = null
        if (blob.size < 200) {
          setMic('idle')
          toast.err('Grabación demasiado corta')
          return
        }
        void finishRecording(blob)
      }
      rec.start()
      startMeter(stream)
      setMic('recording')
    } catch {
      stopMeter()
      toast.err('No se pudo acceder al micrófono')
      setMic('idle')
    }
  }

  async function onCompleteTask(id: number) {
    try {
      await apiCompleteTask(id)
      setMessages((prev) => patchTasksInMessages(prev, id, { status: 'done' }))
      toast.ok('Hecha')
      onAfterChat?.({ tasksChanged: true })
    } catch (e) {
      const msg = String(e)
      setError(msg)
      toast.err(msg)
    }
  }

  async function onStartTask(id: number) {
    try {
      await apiPatchTask(id, { status: 'in_progress' })
      setMessages((prev) =>
        patchTasksInMessages(prev, id, { status: 'in_progress' }),
      )
      toast.ok('En curso')
      onAfterChat?.({ tasksChanged: true })
    } catch (e) {
      const msg = String(e)
      setError(msg)
      toast.err(msg)
    }
  }

  const now = new Date()
  void tick
  const spaceLabel = spaceDef(space).label
  const recClock = `${String(Math.floor(recSecs / 60)).padStart(2, '0')}:${String(recSecs % 60).padStart(2, '0')}`

  return (
    <section className="chat">
      <header className="chat__head">
        <h2>Chat</h2>
        <span className="muted">
          Jone
          {space !== 'all' ? ` · ${spaceLabel}` : ''}
        </span>
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
      <div
        className="chat__log"
        ref={logRef}
        aria-live="polite"
        onScroll={onLogScroll}
      >
        {loadingOlder ? (
          <p className="muted chat__load-older">Cargando…</p>
        ) : hasMore ? (
          <p className="muted chat__load-older">↑ más arriba</p>
        ) : null}
        {messages.length === 0 && !busy ? (
          <div className="chat__empty empty-state">
            <p className="empty-state__title">Habla con Jone</p>
            <p className="muted">
              Escribe, usa el micrófono o pulsa ⌘K. Captura, tareas, memoria.
            </p>
          </div>
        ) : null}
        {messages.map((m, i) => (
          <div
            key={m.id ?? `tmp-${i}-${m.role}-${m.content.slice(0, 24)}`}
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
                    onOpen={onOpenTask}
                    onComplete={onCompleteTask}
                    onStart={onStartTask}
                  />
                ))}
              </div>
            ) : null}
          </div>
        ))}
        {thinking ? (
          <p className="muted chat__thinking chat__thinking--live">{thinking}</p>
        ) : null}
        {busy && !thinking ? (
          <p className="muted chat__thinking">Pensando…</p>
        ) : null}
        <div ref={bottomRef} />
      </div>
      {error ? <p className="error">{error}</p> : null}
      <form
        className={`chat__form${mic === 'recording' ? ' chat__form--rec' : ''}${mic === 'transcribing' ? ' chat__form--busy' : ''}`}
        onSubmit={(e) => {
          e.preventDefault()
          void sendText(text)
        }}
      >
        {mic === 'recording' || mic === 'transcribing' ? (
          <div
            className={`chat__rec${mic === 'transcribing' ? ' is-transcribing' : ''}`}
            role="status"
            aria-live="polite"
          >
            <div className="chat__rec-meta">
              <span className="chat__rec-dot" aria-hidden />
              <span className="chat__rec-label">
                {mic === 'transcribing' ? 'Transcribiendo…' : 'Grabando'}
              </span>
              {mic === 'recording' ? (
                <time className="chat__rec-time">{recClock}</time>
              ) : null}
            </div>
            <div className="chat__wave" aria-hidden>
              {levels.map((v, i) => (
                <span
                  key={i}
                  className="chat__wave-bar"
                  style={{ transform: `scaleY(${v})` }}
                />
              ))}
            </div>
            <p className="chat__rec-hint muted">
              {mic === 'transcribing'
                ? 'Un momento…'
                : 'Habla — toca Stop para parar'}
            </p>
          </div>
        ) : (
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Mensaje, mic o ⌘K…"
            rows={2}
            disabled={busy}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void sendText(text)
              }
            }}
          />
        )}
        <div className="chat__actions">
          <button
            type="button"
            className={`chat__mic${mic === 'recording' ? ' is-recording' : ''}${mic === 'transcribing' ? ' is-busy' : ''}`}
            disabled={busy || mic === 'transcribing'}
            onClick={() => void toggleMic()}
            title={
              mic === 'recording'
                ? 'Parar grabación'
                : mic === 'transcribing'
                  ? 'Transcribiendo…'
                  : 'Voz one-tap'
            }
            aria-label="Micrófono"
          >
            {mic === 'recording' ? 'Stop' : mic === 'transcribing' ? '…' : 'Mic'}
          </button>
          <button type="submit" disabled={busy || mic !== 'idle' || !text.trim()}>
            Enviar
          </button>
        </div>
      </form>
    </section>
  )
})
