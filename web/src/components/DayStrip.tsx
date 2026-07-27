import { useEffect, useState } from 'react'
import { apiDay, type DaySnapshot } from '../api'

type Props = {
  refreshToken?: number
}

function formatAgendaWhen(startsAt: string): string {
  // "2026-07-28T10:00" or date-only → short label
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

export function DayStrip({ refreshToken = 0 }: Props) {
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
      <section className="day-strip day-strip--err">
        <p className="muted">{error}</p>
      </section>
    )
  }

  if (!day) {
    return (
      <section className="day-strip">
        <p className="muted">Cargando el día…</p>
      </section>
    )
  }

  return (
    <section className="day-strip" aria-label="Hoy">
      <div className="day-strip__main">
        <div className="day-strip__when">
          <h2>{day.headline}</h2>
          <p className="day-strip__clock">{day.clock.split(', ')[1] ?? ''}</p>
        </div>
        <div className="day-strip__counts">
          <span>
            <strong>{day.tasks.in_progress}</strong> en curso
          </span>
          <span>
            <strong>{day.tasks.open}</strong> pendientes
          </span>
        </div>
      </div>

      <div className="day-strip__cols">
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
            <p className="muted">Sin dream aún — /dream o el cron de las 09:00</p>
          )}
        </div>
      </div>
    </section>
  )
}
