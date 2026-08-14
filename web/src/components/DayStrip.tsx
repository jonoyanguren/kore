import { useEffect, useState, type ReactNode, type SVGProps } from 'react'
import {
  apiDay,
  apiGmailMarkRead,
  apiGmailReplyDraft,
  apiGmailReplySend,
  apiGmailToTask,
  apiCalendarEventToTask,
  apiCalendarEventPrep,
  type DaySnapshot,
  type GmailReplyDraft,
} from '../api'
import { formatWhen } from '../dates'
import { dailyQuote } from '../lib/quotes'
import { DayCalendar, type DayMeeting } from './DayCalendar'
import { ProjectChip } from './ProjectChip'
import { useToast } from './Toasts'

type Props = {
  refreshToken?: number
  variant?: 'hero' | 'rail'
  onOpenBoard?: () => void
}

function clockParts(clock: string): { time: string; rest: string } {
  const m = clock.match(/(\d{1,2}:\d{2})(?!.*\d{1,2}:\d{2})/)
  if (!m) return { time: '', rest: clock }
  return {
    time: m[1],
    rest: clock.replace(`, ${m[1]}`, '').replace(m[1], '').trim(),
  }
}

function InboxIcon({ children, ...rest }: SVGProps<SVGSVGElement> & { children: ReactNode }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...rest}
    >
      {children}
    </svg>
  )
}

function IconReply() {
  return (
    <InboxIcon>
      {/* reply arrow */}
      <polyline points="9 17 4 12 9 7" />
      <path d="M20 18v-2a4 4 0 0 0-4-4H4" />
    </InboxIcon>
  )
}

function IconTask() {
  return (
    <InboxIcon>
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <path d="M8 12l3 3 5-6" />
    </InboxIcon>
  )
}

function IconRead() {
  return (
    <InboxIcon>
      <path d="M20 6L9 17l-5-5" />
    </InboxIcon>
  )
}

export function DayStrip({
  refreshToken = 0,
  variant = 'rail',
  onOpenBoard,
}: Props) {
  const [day, setDay] = useState<DaySnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [busyKind, setBusyKind] = useState<'reply' | 'task' | 'prep' | null>(
    null,
  )
  const [calBusyId, setCalBusyId] = useState<string | null>(null)
  const [calBusyKind, setCalBusyKind] = useState<'task' | 'prep' | null>(null)
  const [calPrep, setCalPrep] = useState<{
    title: string
    starts_at?: string | null
    html_link?: string | null
    text: string
  } | null>(null)
  const [reply, setReply] = useState<GmailReplyDraft | null>(null)
  const [replyBody, setReplyBody] = useState('')
  const [replyBusy, setReplyBusy] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const toast = useToast()

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const snap = await apiDay()
        if (!cancelled) {
          setDay(snap)
          setError(null)
        }
      } catch (e) {
        if (!cancelled) setError(String(e))
      }
    }
    void load()
    const id = window.setInterval(() => void load(), 60_000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [refreshToken])

  if (error && !day) {
    return (
      <section className={`day-strip day-strip--${variant} day-strip--err`}>
        <p className="muted">{error}</p>
      </section>
    )
  }

  if (!day) {
    return (
      <section className={`day-strip day-strip--${variant}`}>
        <p className="muted">Cargando…</p>
      </section>
    )
  }

  const { time, rest } = clockParts(day.clock)
  const briefing = day.briefing
  const summary = briefing?.summary ?? []
  const starred = briefing?.in_progress_tasks ?? []
  const mustNotMiss = briefing?.must_not_miss ?? []
  const important = briefing?.important_tasks ?? []
  const meetings = briefing?.meetings ?? day.agenda ?? []
  const help = briefing?.help ?? []
  const inbox = day.inbox
  const dreamInbox = briefing?.inbox ?? []
  const markedToday = inbox?.marked_read_today ?? []
  const focusTasks = Array.from(
    new Map([...starred, ...mustNotMiss].map((t) => [t.id, t])).values(),
  )

  async function markRead(id: string) {
    const msg = day?.inbox?.messages.find((m) => m.id === id)
    const ok = await apiGmailMarkRead(id)
    if (!ok || !day?.inbox) return
    setDay({
      ...day,
      inbox: {
        ...day.inbox,
        messages: day.inbox.messages.filter((m) => m.id !== id),
        marked_read_today: msg
          ? [
              {
                at: Date.now() / 1000,
                message_id: id,
                subject: msg.subject,
                from: msg.from,
                permalink: msg.permalink,
                reason: 'manual',
              },
              ...(day.inbox.marked_read_today ?? []),
            ]
          : day.inbox.marked_read_today,
      },
    })
  }

  async function toTask(id: string) {
    if (busyId) return
    setBusyId(id)
    setBusyKind('task')
    const msg = day?.inbox?.messages.find((m) => m.id === id)
    try {
      const { task } = await apiGmailToTask(id)
      toast.ok(`Tarea: ${task.title}`)
      if (day?.inbox) {
        setDay({
          ...day,
          inbox: {
            ...day.inbox,
            messages: day.inbox.messages.filter((m) => m.id !== id),
            marked_read_today: msg
              ? [
                  {
                    at: Date.now() / 1000,
                    message_id: id,
                    subject: msg.subject,
                    from: msg.from,
                    permalink: msg.permalink,
                    reason: 'task',
                  },
                  ...(day.inbox.marked_read_today ?? []),
                ]
              : day.inbox.marked_read_today,
          },
        })
      }
    } catch (e) {
      toast.err(String(e))
    } finally {
      setBusyId(null)
      setBusyKind(null)
    }
  }

  async function calToTask(ev: DayMeeting) {
    if (calBusyId) return
    const id = String(ev.id)
    setCalBusyId(id)
    setCalBusyKind('task')
    try {
      const { task } = await apiCalendarEventToTask(ev)
      toast.ok(`Tarea: ${task.title}`)
    } catch (e) {
      toast.err(String(e))
    } finally {
      setCalBusyId(null)
      setCalBusyKind(null)
    }
  }

  async function runCalPrep(ev: DayMeeting) {
    if (calBusyId) return
    const id = String(ev.id)
    setCalBusyId(id)
    setCalBusyKind('prep')
    try {
      const { prep, event } = await apiCalendarEventPrep(ev)
      setCalPrep({
        title: String(event?.title || ev.title || 'Cita'),
        starts_at: event?.starts_at ?? ev.starts_at,
        html_link: event?.html_link ?? ev.html_link,
        text: prep,
      })
    } catch (e) {
      toast.err(String(e))
    } finally {
      setCalBusyId(null)
      setCalBusyKind(null)
    }
  }

  async function openReply(id: string) {
    if (busyId || replyBusy) return
    if (day?.inbox && day.inbox.can_send === false) {
      toast.err(
        'Falta permiso de envío. Desconecta y reconecta Gmail en Más.',
      )
      return
    }
    setBusyId(id)
    setBusyKind('reply')
    try {
      const draft = await apiGmailReplyDraft(id)
      setReply(draft)
      setReplyBody(draft.body)
    } catch (e) {
      toast.err(String(e))
    } finally {
      setBusyId(null)
      setBusyKind(null)
    }
  }

  async function sendReply() {
    if (!reply || replyBusy) return
    const text = replyBody.trim()
    if (!text) {
      toast.err('El cuerpo está vacío')
      return
    }
    setReplyBusy(true)
    try {
      const sent = await apiGmailReplySend(reply.message_id, text)
      toast.ok(`Enviado a ${sent.to}`)
      const id = reply.message_id
      const msg = day?.inbox?.messages.find((m) => m.id === id)
      if (day?.inbox) {
        setDay({
          ...day,
          inbox: {
            ...day.inbox,
            messages: day.inbox.messages.filter((m) => m.id !== id),
            marked_read_today: msg
              ? [
                  {
                    at: Date.now() / 1000,
                    message_id: id,
                    subject: msg.subject,
                    from: msg.from,
                    permalink: msg.permalink,
                    reason: 'reply',
                  },
                  ...(day.inbox.marked_read_today ?? []),
                ]
              : day.inbox.marked_read_today,
          },
        })
      }
      setReply(null)
      setReplyBody('')
    } catch (e) {
      toast.err(String(e))
    } finally {
      setReplyBusy(false)
    }
  }

  const dateLine = rest || day.headline || ''
  const focusTask = starred[0] ?? mustNotMiss[0] ?? important[0]
  const quote = dailyQuote(day.today)

  if (variant === 'rail') {
    const nextMeeting = meetings[0]
    return (
      <section className="day-strip day-strip--rail" aria-label="Hoy">
        <div className="day-strip__rail-main">
          <strong className="day-strip__rail-head">{day.headline}</strong>
          <span className="day-strip__rail-clock">{time || day.clock}</span>
          <span className="muted">
            {day.tasks.in_progress} en curso · {day.tasks.open} abiertas
          </span>
        </div>
        <p className="day-strip__rail-next muted">
          {nextMeeting
            ? `Reunión: ${formatWhen(nextMeeting.starts_at)} — ${nextMeeting.title}`
            : focusTask
              ? `Foco: ${focusTask.title}`
              : summary[0]
                ? summary[0]
                : help[0]
                  ? help[0]
                  : 'Sin briefing aún'}
        </p>
      </section>
    )
  }

  return (
    <section className="day-strip day-strip--hero" aria-label="Hoy">
      {dateLine ? <p className="day-strip__hero-date">{dateLine}</p> : null}
      {time ? <p className="day-strip__hero-clock">{time}</p> : null}

      <blockquote className="day-strip__quote">
        <p className="day-strip__quote-text">{quote.text}</p>
        {quote.author ? (
          <footer className="day-strip__quote-author">
            — {quote.author}
          </footer>
        ) : null}
      </blockquote>

      <div className="day-strip__brief">
        <div className="day-strip__block">
          <h3>Resumen</h3>
          {summary.length === 0 ? (
            <p className="muted">
              {briefing?.has_dream
                ? 'Sin resumen en el dream'
                : 'Abre esta vista tras las 09:00 — el dream alimenta el Día (sin Telegram)'}
            </p>
          ) : (
            <div className="day-strip__summary">
              {summary.map((line) => (
                <p key={line}>{line}</p>
              ))}
            </div>
          )}
        </div>

        <div className="day-strip__block">
          <h3>Reuniones</h3>
          {day.calendar?.error ? (
            <p className="muted">
              {day.calendar.error_code === 'api_disabled' ? (
                <>
                  Activa{' '}
                  <a
                    href="https://console.cloud.google.com/apis/library/calendar-json.googleapis.com"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Google Calendar API
                  </a>{' '}
                  en el proyecto GCP del OAuth (Enable). Luego recarga Día —
                  no hace falta reconectar.
                </>
              ) : day.calendar.error_code === 'needs_reconnect' ? (
                <>
                  {day.calendar.error}{' '}
                  <a href="/api/gmail/connect">Reconectar</a>
                </>
              ) : (
                day.calendar.error
              )}
            </p>
          ) : null}
          {meetings.length === 0 && !day.calendar?.error ? (
            <p className="muted">
              {day.calendar?.ready === false && day.inbox?.connected
                ? 'Reconecta Google para ver Calendar'
                : 'Nada próximo'}
            </p>
          ) : null}
          {meetings.length > 0 ? (
            <DayCalendar
              today={day.today}
              meetings={meetings}
              busyId={calBusyId}
              busyKind={calBusyKind}
              onToTask={calToTask}
              onPrep={runCalPrep}
            />
          ) : null}
          {calPrep ? (
            <div className="day-cal__prep">
              <div className="day-cal__prep-head">
                <strong>Prep · {calPrep.title}</strong>
                <button
                  type="button"
                  className="ghost day-cal__act"
                  onClick={() => setCalPrep(null)}
                >
                  Cerrar
                </button>
              </div>
              {calPrep.starts_at ? (
                <p className="muted day-cal__prep-when">
                  {formatWhen(calPrep.starts_at)}
                  {calPrep.html_link ? (
                    <>
                      {' · '}
                      <a
                        href={calPrep.html_link}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Abrir
                      </a>
                    </>
                  ) : null}
                </p>
              ) : null}
              <pre className="day-cal__prep-body">{calPrep.text}</pre>
            </div>
          ) : null}
        </div>

        <div className="day-strip__block">
          <h3>Foco</h3>
          {focusTasks.length === 0 ? (
            <p className="muted">Sin tareas del día</p>
          ) : (
            <>
              <ul>
                {focusTasks.slice(0, 6).map((t) => (
                  <li key={t.id}>
                    <button
                      type="button"
                      className="day-strip__task-link"
                      onClick={onOpenBoard}
                    >
                      {t.title}
                    </button>
                    <span className="day-strip__tag">
                      <ProjectChip project={t.project} />
                      {t.due_at
                        ? formatWhen(
                            t.due_at.length === 10
                              ? `${t.due_at}T00:00`
                              : t.due_at,
                          )
                        : null}
                    </span>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="day-strip__all"
                onClick={onOpenBoard}
              >
                Ver todas en el board →
              </button>
            </>
          )}
        </div>

        <div className="day-strip__block">
          <h3>Inbox</h3>
          {!inbox?.connected ? (
            <div className="day-strip__inbox-state">
              <p className="day-strip__inbox-lead">Gmail aún no está conectado</p>
              <p className="muted">Ábrelo en Más → Gmail para ver unread aquí.</p>
            </div>
          ) : inbox.error ? (
            <div className="day-strip__inbox-state day-strip__inbox-state--warn">
              <p className="day-strip__inbox-lead">
                {inbox.error_code === 'needs_reconnect'
                  ? 'Hay que volver a autorizar Gmail'
                  : 'No se pudo cargar el correo'}
              </p>
              <p className="muted">
                {inbox.error ||
                  'En Más → Gmail, desconecta y vuelve a conectar.'}
              </p>
              <a className="day-strip__inbox-cta" href="/api/gmail/connect">
                Reconectar Gmail
              </a>
            </div>
          ) : inbox.messages.length === 0 ? (
            <div className="day-strip__inbox-state">
              {dreamInbox.length > 0 ? (
                <>
                  <p className="day-strip__inbox-lead">Del dream</p>
                  <ul className="day-strip__inbox-dream">
                    {dreamInbox.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                  <p className="muted">Sin unread ahora en Gmail.</p>
                </>
              ) : (
                <>
                  <p className="day-strip__inbox-lead">Bandeja tranquila</p>
                  <p className="muted">Sin unread de los últimos días.</p>
                </>
              )}
            </div>
          ) : (
            <>
              <ul className="day-strip__inbox">
              {inbox.messages.map((m) => (
                <li key={m.id}>
                  <a
                    href={m.permalink}
                    target="_blank"
                    rel="noreferrer"
                    className="day-strip__task-link"
                  >
                    {m.subject}
                  </a>
                  <span className="day-strip__tag muted">{m.from}</span>
                  <div className="day-strip__inbox-actions">
                    <button
                      type="button"
                      className="ghost day-strip__inbox-btn"
                      title="Responder"
                      aria-label="Responder"
                      disabled={busyId === m.id || replyBusy}
                      onClick={() => void openReply(m.id)}
                    >
                      <IconReply />
                      <span>
                        {busyId === m.id && busyKind === 'reply' ? '…' : 'Resp.'}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="ghost day-strip__inbox-btn"
                      title="Pasar a tarea"
                      aria-label="Pasar a tarea"
                      disabled={busyId === m.id || replyBusy}
                      onClick={() => void toTask(m.id)}
                    >
                      <IconTask />
                      <span>
                        {busyId === m.id && busyKind === 'task' ? '…' : 'Tarea'}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="ghost day-strip__inbox-btn"
                      title="Marcar leído"
                      aria-label="Marcar leído"
                      disabled={busyId === m.id || replyBusy}
                      onClick={() => void markRead(m.id)}
                    >
                      <IconRead />
                      <span>Leído</span>
                    </button>
                  </div>
                </li>
              ))}
              </ul>
              {reply ? (
                <div className="day-strip__reply">
                  <p className="day-strip__reply-meta">
                    <strong>Para</strong> {reply.to}
                    <span className="muted"> · {reply.subject}</span>
                  </p>
                  <textarea
                    className="day-strip__reply-body"
                    rows={8}
                    value={replyBody}
                    onChange={(e) => setReplyBody(e.target.value)}
                    disabled={replyBusy}
                    aria-label="Borrador de respuesta"
                  />
                  <div className="day-strip__reply-actions">
                    <button
                      type="button"
                      className="ghost"
                      disabled={replyBusy}
                      onClick={() => {
                        setReply(null)
                        setReplyBody('')
                      }}
                    >
                      Cancelar
                    </button>
                    <button
                      type="button"
                      disabled={replyBusy || !replyBody.trim()}
                      onClick={() => void sendReply()}
                    >
                      {replyBusy ? 'Enviando…' : 'Enviar'}
                    </button>
                  </div>
                </div>
              ) : null}
            </>
          )}
          {markedToday.length > 0 ? (
            <div className="day-strip__marked">
              <h4 className="day-strip__marked-h">Marcados leídos hoy</h4>
              <ul className="day-strip__marked-list">
                {markedToday.map((e) => (
                  <li key={`${e.message_id}-${e.at}`}>
                    <a
                      href={e.permalink || undefined}
                      target="_blank"
                      rel="noreferrer"
                      className="day-strip__task-link"
                    >
                      {e.subject}
                    </a>
                    <span className="day-strip__tag muted">
                      {e.reason === 'task'
                        ? '→ tarea'
                        : e.reason === 'reply'
                          ? '→ reply'
                          : e.from}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>

        <div className="day-strip__block">
          <h3>Ayuda</h3>
          {help.length === 0 ? (
            <p className="muted">
              {briefing?.has_dream
                ? 'Sin notas de ayuda en el dream'
                : 'Sin dream aún — cron 09:00 o /dream en el chat de la consola'}
            </p>
          ) : (
            <>
              <ul className="day-strip__help">
                {(helpOpen ? help : help.slice(0, 3)).map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              {help.length > 3 ? (
                <button
                  type="button"
                  className="ghost day-strip__help-toggle"
                  onClick={() => setHelpOpen((v) => !v)}
                >
                  {helpOpen
                    ? 'Menos'
                    : `Mostrar ${help.length - 3} más`}
                </button>
              ) : null}
            </>
          )}
        </div>
      </div>
    </section>
  )
}
