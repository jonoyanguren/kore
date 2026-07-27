import { useEffect, useState } from 'react'
import { apiDay, type DaySnapshot } from '../api'

type Props = {
  refreshToken?: number
  variant?: 'hero' | 'rail'
  onOpenChat?: () => void
  onOpenBoard?: () => void
}

function formatAgendaWhen(startsAt: string): string {
  const m = startsAt.match(/T(\d{2}:\d{2})/)
  const day = startsAt.slice(0, 10)
  const today = new Date().toLocaleDateString('en-CA', {
    timeZone: 'Europe/Madrid',
  })
  const time = m ? m[1] : ''
  if (day === today) return time ? `hoy ${time}` : 'hoy'
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  const tom = tomorrow.toLocaleDateString('en-CA', {
    timeZone: 'Europe/Madrid',
  })
  if (day === tom) return time ? `mañana ${time}` : 'mañana'
  return time ? `${day.slice(5)} ${time}` : day.slice(5)
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
}: Props) {
  const [day, setDay] = useState<DaySnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const snap = await apiDay()
        if (!cancelled) {
          setDay(snap)
          setError(null)
        }
      } catch (e) {
        if (!cancelled) setError(String(e))
      }
    })()
    return () => {
      cancelled = true
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
  const important = briefing?.important_tasks ?? []
  const meetings = briefing?.meetings ?? day.agenda ?? []
  const help = briefing?.help ?? []
  // "lunes 27 de julio de 2026" → weekday + date once (not repeated)
  const dateLine = rest || day.headline || ''

  if (variant === 'rail') {
    const nextMeeting = meetings[0]
    const topTask = important[0]
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
            : topTask
              ? `Foco: ${topTask.title}`
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
          <h3>Tareas importantes</h3>
          {important.length === 0 ? (
            <p className="muted">Ninguna destacada</p>
          ) : (
            <ul>
              {important.map((t) => (
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
                  </span>
                </li>
              ))}
            </ul>
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
          <h3>Ayuda</h3>
          {help.length === 0 ? (
            <p className="muted">
              {briefing?.has_dream
                ? 'Sin notas de ayuda en el dream'
                : 'Sin dream aún — /dream o el cron de las 09:00'}
            </p>
          ) : (
            <ul className="day-strip__help">
              {help.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
          <button
            type="button"
            className="ghost day-strip__cta"
            onClick={onOpenChat}
          >
            Hablar con Jone →
          </button>
        </div>
      </div>
    </section>
  )
}
