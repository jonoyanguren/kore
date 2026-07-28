import { useEffect, useState } from 'react'
import { apiDay, type DaySnapshot } from '../api'

type Props = {
  refreshToken?: number
  variant?: 'hero' | 'rail'
  onOpenChat?: () => void
  onOpenBoard?: () => void
  onOpenMemory?: () => void
}

const MONTHS_ES_SHORT = [
  'Ene',
  'Feb',
  'Mar',
  'Abr',
  'May',
  'Jun',
  'Jul',
  'Ago',
  'Sep',
  'Oct',
  'Nov',
  'Dic',
]

function formatAgendaWhen(startsAt: string): string {
  const m = startsAt.match(/T(\d{2}:\d{2})/)
  const day = startsAt.slice(0, 10)
  const today = new Date().toLocaleDateString('en-CA', {
    timeZone: 'Europe/Madrid',
  })
  // All-day / date-only dues often land as T00:00 — don't show midnight.
  const time = m && m[1] !== '00:00' ? m[1] : ''
  if (day === today) return time ? `hoy ${time}` : 'hoy'

  // Compare calendar days in Madrid, not local browser TZ +1 day
  const tomDate = new Date(`${today}T12:00:00`)
  tomDate.setDate(tomDate.getDate() + 1)
  const tom = tomDate.toLocaleDateString('en-CA', { timeZone: 'Europe/Madrid' })
  if (day === tom) return time ? `mañana ${time}` : 'mañana'

  const y = Number(day.slice(0, 4))
  const mo = Number(day.slice(5, 7))
  const d = Number(day.slice(8, 10))
  if (!y || !mo || !d) return day
  const label = `${String(d).padStart(2, '0')}-${MONTHS_ES_SHORT[mo - 1]}`
  return time ? `${label} ${time}` : label
}

function clockParts(clock: string): { time: string; rest: string } {
  const m = clock.match(/(\d{1,2}:\d{2})(?!.*\d{1,2}:\d{2})/)
  if (!m) return { time: '', rest: clock }
  return {
    time: m[1],
    rest: clock.replace(`, ${m[1]}`, '').replace(m[1], '').trim(),
  }
}

const STATUS_SHORT: Record<string, string> = {
  in_progress: 'en curso',
  open: 'pendiente',
}

export function DayStrip({
  refreshToken = 0,
  variant = 'rail',
  onOpenChat,
  onOpenBoard,
  onOpenMemory,
}: Props) {
  const [day, setDay] = useState<DaySnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)

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
    // Soft poll so vista Día picks up the 09:00 dream without Telegram.
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
  // "lunes 27 de julio de 2026" → weekday + date once (not repeated)
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
            ? `Reunión: ${formatAgendaWhen(nextMeeting.starts_at)} — ${nextMeeting.title}`
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
                    {formatAgendaWhen(a.starts_at)}
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
                    {t.project ? t.project : 'en curso'}
                    {t.due_at
                      ? ` · ${formatAgendaWhen(t.due_at.length === 10 ? `${t.due_at}T00:00` : t.due_at)}`
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
                    {STATUS_SHORT[t.status] ?? t.status}
                    {t.project ? ` · ${t.project}` : ''}
                    {t.due_at
                      ? ` · ${formatAgendaWhen(t.due_at.length === 10 ? `${t.due_at}T00:00` : t.due_at)}`
                      : ''}
                  </span>
                </li>
              ))}
            </ul>
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
          <div className="day-strip__ctas">
            <button
              type="button"
              className="ghost day-strip__cta"
              onClick={onOpenMemory ?? onOpenChat}
            >
              {onOpenMemory ? 'Memoria / diario →' : 'Hablar con Jone →'}
            </button>
            {onOpenMemory && onOpenChat ? (
              <button
                type="button"
                className="ghost day-strip__cta"
                onClick={onOpenChat}
              >
                Hablar con Jone →
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  )
}
