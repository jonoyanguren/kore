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
  // "lunes, 27 de julio de 2026, 13:45" or similar — take last HH:MM
  const m = clock.match(/(\d{1,2}:\d{2})(?!.*\d{1,2}:\d{2})/)
  if (!m) return { time: '', rest: clock }
  return { time: m[1], rest: clock.replace(`, ${m[1]}`, '').replace(m[1], '').trim() }
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

  if (variant === 'rail') {
    return (
      <section className="day-strip day-strip--rail" aria-label="Hoy">
        <div className="day-strip__rail-main">
          <strong className="day-strip__rail-head">{day.headline}</strong>
          <span className="day-strip__rail-clock">{time || day.clock}</span>
          <span className="muted">
            {day.tasks.in_progress} en curso · {day.tasks.open} abiertas
          </span>
        </div>
        {day.agenda[0] ? (
          <p className="day-strip__rail-next muted">
            Próximo: {formatAgendaWhen(day.agenda[0].starts_at)} —{' '}
            {day.agenda[0].title}
          </p>
        ) : null}
      </section>
    )
  }

  return (
    <section className="day-strip day-strip--hero" aria-label="Hoy">
      <p className="day-strip__eyebrow">{rest || day.headline}</p>
      <h2 className="day-strip__hero-title">{day.headline}</h2>
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

      <div className="day-strip__hero-grid">
        <div className="day-strip__block">
          <h3>Agenda</h3>
          {day.agenda.length === 0 ? (
            <p className="muted">Nada próximo</p>
          ) : (
            <ul>
              {day.agenda.map((a) => (
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
          <h3>
            Briefing
            {day.dream ? (
              <span className="muted"> · {day.dream.day}</span>
            ) : null}
          </h3>
          {day.dream ? (
            <p className="day-strip__dream">{day.dream.excerpt}</p>
          ) : (
            <p className="muted">Sin dream aún</p>
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
