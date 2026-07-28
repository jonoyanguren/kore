import { useEffect, useState } from 'react'
import {
  apiDay,
  apiGmailMarkRead,
  apiGmailToTask,
  type DaySnapshot,
} from '../api'
import { formatWhen } from '../dates'
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

export function DayStrip({
  refreshToken = 0,
  variant = 'rail',
  onOpenBoard,
}: Props) {
  const [day, setDay] = useState<DaySnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
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

  async function markRead(id: string) {
    const ok = await apiGmailMarkRead(id)
    if (!ok || !day?.inbox) return
    setDay({
      ...day,
      inbox: {
        ...day.inbox,
        messages: day.inbox.messages.filter((m) => m.id !== id),
      },
    })
  }

  async function toTask(id: string) {
    if (busyId) return
    setBusyId(id)
    try {
      const { task } = await apiGmailToTask(id)
      toast.ok(`Tarea: ${task.title}`)
      await markRead(id)
    } catch (e) {
      toast.err(String(e))
    } finally {
      setBusyId(null)
    }
  }

  const dateLine = rest || day.headline || ''
  const focusTask = starred[0] ?? mustNotMiss[0] ?? important[0]

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
      <h2 className="day-strip__hero-title">
        {day.greeting || `Hola, ${day.owner_name || 'Jon'}`}
      </h2>
      {dateLine ? <p className="day-strip__hero-date">{dateLine}</p> : null}
      {time ? <p className="day-strip__hero-clock">{time}</p> : null}

      <div className="day-strip__hero-counts">
        <button type="button" className="day-strip__stat" onClick={onOpenBoard}>
          <strong>{day.tasks.in_progress}</strong>
          <span>en curso</span>
        </button>
        <button type="button" className="day-strip__stat" onClick={onOpenBoard}>
          <strong>{day.tasks.open}</strong>
          <span>pendientes</span>
        </button>
      </div>

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
          {meetings.length === 0 ? (
            <p className="muted">Nada próximo</p>
          ) : (
            <ul>
              {meetings.map((a) => (
                <li key={a.id}>
                  <span className="day-strip__ag-when">
                    {formatWhen(a.starts_at)}
                  </span>
                  {a.title}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="day-strip__block">
          <h3>★ En curso</h3>
          {starred.length === 0 ? (
            <p className="muted">Nada con estrella — márcalas en Tareas</p>
          ) : (
            <ul>
              {starred.map((t) => (
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
                      : !t.project
                        ? 'en curso'
                        : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="day-strip__block">
          <h3>No se pueden escapar</h3>
          {mustNotMiss.length === 0 ? (
            <p className="muted">Ninguna ahora</p>
          ) : (
            <ul>
              {mustNotMiss.map((t) => (
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
              {dreamInbox.length > 0 ? (
                <ul className="day-strip__inbox-dream">
                  {dreamInbox.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              ) : null}
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
                      className="ghost day-strip__inbox-task"
                      title="Pasar a tarea"
                      aria-label="Pasar a tarea"
                      disabled={busyId === m.id}
                      onClick={() => void toTask(m.id)}
                    >
                      <span aria-hidden="true">☑</span>
                      <span className="day-strip__inbox-task-label">
                        {busyId === m.id ? '…' : 'Tarea'}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="ghost day-strip__inbox-read"
                      disabled={busyId === m.id}
                      onClick={() => void markRead(m.id)}
                    >
                      Leído
                    </button>
                  </div>
                </li>
              ))}
              </ul>
            </>
          )}
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
            <ul className="day-strip__help">
              {help.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  )
}
