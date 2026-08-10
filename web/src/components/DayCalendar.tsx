import { useMemo, useState } from 'react'

export type DayMeeting = {
  id: number | string
  starts_at: string
  title: string
  status: string
  source?: string
  calendar?: string
  html_link?: string | null
  ends_at?: string | null
  all_day?: boolean
}

type Props = {
  today: string
  meetings: DayMeeting[]
  busyId?: string | null
  busyKind?: 'task' | 'prep' | null
  onToTask?: (ev: DayMeeting) => void
  onPrep?: (ev: DayMeeting) => void
}

const HOUR_PX = 56
const DEFAULT_MINUTES = 45
const MIN_EVENT_PX = 52
const DAY_NAMES = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb']

function madridTodayIso(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Europe/Madrid' })
}

function addDaysIso(iso: string, days: number): string {
  const d = new Date(`${iso}T12:00:00`)
  d.setDate(d.getDate() + days)
  return d.toLocaleDateString('en-CA', { timeZone: 'Europe/Madrid' })
}

function dayLabel(iso: string, today: string): string {
  if (iso === today) return 'Hoy'
  if (iso === addDaysIso(today, 1)) return 'Mañana'
  const d = new Date(`${iso}T12:00:00`)
  const wd = DAY_NAMES[d.getDay()]
  return `${wd} ${iso.slice(8, 10)}`
}

function parseMinutes(stamp: string): number | null {
  const m = stamp.match(/T(\d{2}):(\d{2})/)
  if (!m) return null
  return Number(m[1]) * 60 + Number(m[2])
}

function isAllDay(ev: DayMeeting): boolean {
  if (ev.all_day) return true
  if (!ev.starts_at.includes('T')) return true
  const t = ev.starts_at.match(/T(\d{2}:\d{2})/)
  return Boolean(t && t[1] === '00:00' && !ev.ends_at?.includes('T'))
}

function eventEndMinutes(ev: DayMeeting, startMin: number): number {
  if (ev.ends_at) {
    const end = parseMinutes(ev.ends_at)
    if (end != null && end > startMin) return end
  }
  return startMin + DEFAULT_MINUTES
}

function madridNowMinutes(): number {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Madrid',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(new Date())
  const h = Number(parts.find((p) => p.type === 'hour')?.value || 0)
  const m = Number(parts.find((p) => p.type === 'minute')?.value || 0)
  return h * 60 + m
}

type LaidOut = {
  ev: DayMeeting
  top: number
  height: number
  startLabel: string
  endLabel: string
  col: number
  cols: number
  short: boolean
}

function layoutTimed(events: DayMeeting[], rangeStart: number): LaidOut[] {
  const items = events
    .map((ev) => {
      const start = parseMinutes(ev.starts_at)
      if (start == null) return null
      const end = eventEndMinutes(ev, start)
      return { ev, start, end }
    })
    .filter((x): x is { ev: DayMeeting; start: number; end: number } => x != null)
    .sort((a, b) => a.start - b.start || a.end - b.end)

  const active: { end: number; col: number }[] = []
  const withCol: { ev: DayMeeting; start: number; end: number; col: number }[] =
    []
  for (const it of items) {
    for (let i = active.length - 1; i >= 0; i--) {
      if (active[i].end <= it.start) active.splice(i, 1)
    }
    const used = new Set(active.map((a) => a.col))
    let col = 0
    while (used.has(col)) col += 1
    active.push({ end: it.end, col })
    withCol.push({ ...it, col })
  }

  const result: LaidOut[] = []
  let i = 0
  while (i < withCol.length) {
    let clusterEnd = withCol[i].end
    let j = i + 1
    while (j < withCol.length && withCol[j].start < clusterEnd) {
      clusterEnd = Math.max(clusterEnd, withCol[j].end)
      j += 1
    }
    const cluster = withCol.slice(i, j)
    const cols = Math.max(...cluster.map((c) => c.col)) + 1
    for (const c of cluster) {
      const durationPx = ((c.end - c.start) / 60) * HOUR_PX
      const height = Math.max(durationPx, MIN_EVENT_PX)
      const minutes = c.end - c.start
      result.push({
        ev: c.ev,
        top: ((c.start - rangeStart) / 60) * HOUR_PX,
        height,
        startLabel: `${String(Math.floor(c.start / 60)).padStart(2, '0')}:${String(c.start % 60).padStart(2, '0')}`,
        endLabel: `${String(Math.floor(c.end / 60)).padStart(2, '0')}:${String(c.end % 60).padStart(2, '0')}`,
        col: c.col,
        cols,
        short: minutes <= 35,
      })
    }
    i = j
  }
  return result
}

function EventTitle({
  ev,
  title,
  className,
}: {
  ev: DayMeeting
  title: string
  className?: string
}) {
  if (ev.html_link) {
    return (
      <a
        className={className ? `${className} day-cal__ev-title--link` : 'day-cal__ev-title day-cal__ev-title--link'}
        href={ev.html_link}
        target="_blank"
        rel="noopener noreferrer"
        title="Abrir en Google Calendar"
      >
        {title}
      </a>
    )
  }
  return <strong className={className || 'day-cal__ev-title'}>{title}</strong>
}

function EventActions({
  ev,
  busyId,
  busyKind,
  onToTask,
  onPrep,
}: {
  ev: DayMeeting
  busyId?: string | null
  busyKind?: 'task' | 'prep' | null
  onToTask?: (ev: DayMeeting) => void
  onPrep?: (ev: DayMeeting) => void
}) {
  const id = String(ev.id)
  const busy = busyId === id
  if (!onToTask && !onPrep) return null
  return (
    <div className="day-cal__actions" onClick={(e) => e.stopPropagation()}>
      {onToTask ? (
        <button
          type="button"
          className="day-cal__act"
          disabled={busy}
          onClick={() => onToTask(ev)}
        >
          {busy && busyKind === 'task' ? '…' : 'Tarea'}
        </button>
      ) : null}
      {onPrep ? (
        <button
          type="button"
          className="day-cal__act"
          disabled={busy}
          onClick={() => onPrep(ev)}
        >
          {busy && busyKind === 'prep' ? '…' : 'Prep'}
        </button>
      ) : null}
    </div>
  )
}

export function DayCalendar({
  today,
  meetings,
  busyId,
  busyKind,
  onToTask,
  onPrep,
}: Props) {
  const baseToday = today || madridTodayIso()
  const days = useMemo(
    () => [0, 1, 2, 3].map((n) => addDaysIso(baseToday, n)),
    [baseToday],
  )
  const [selected, setSelected] = useState(days[0])
  const day = days.includes(selected) ? selected : days[0]

  const dayEvents = useMemo(
    () => meetings.filter((m) => (m.starts_at || '').slice(0, 10) === day),
    [meetings, day],
  )
  const allDay = dayEvents.filter(isAllDay)
  const timed = dayEvents.filter((e) => !isAllDay(e))

  const { rangeStart, hours, laid, nowTop } = useMemo(() => {
    let minH = 8
    let maxH = 20
    for (const ev of timed) {
      const s = parseMinutes(ev.starts_at)
      if (s == null) continue
      const e = eventEndMinutes(ev, s)
      minH = Math.min(minH, Math.floor(s / 60))
      maxH = Math.max(maxH, Math.ceil(e / 60))
    }
    minH = Math.max(0, Math.min(minH, 8))
    maxH = Math.min(24, Math.max(maxH, 20))
    if (maxH <= minH) maxH = minH + 1
    const rangeStart = minH * 60
    const hours = Array.from({ length: maxH - minH }, (_, i) => minH + i)
    const laid = layoutTimed(timed, rangeStart)
    let nowTop: number | null = null
    if (day === madridTodayIso()) {
      const now = madridNowMinutes()
      if (now >= rangeStart && now <= maxH * 60) {
        nowTop = ((now - rangeStart) / 60) * HOUR_PX
      }
    }
    return { rangeStart, hours, laid, nowTop }
  }, [timed, day])

  const counts = useMemo(() => {
    const map = new Map<string, number>()
    for (const d of days) map.set(d, 0)
    for (const m of meetings) {
      const d = (m.starts_at || '').slice(0, 10)
      if (map.has(d)) map.set(d, (map.get(d) || 0) + 1)
    }
    return map
  }, [days, meetings])

  if (meetings.length === 0) return null

  return (
    <div className="day-cal">
      <div className="day-cal__tabs" role="tablist" aria-label="Días">
        {days.map((d) => {
          const n = counts.get(d) || 0
          return (
            <button
              key={d}
              type="button"
              role="tab"
              aria-selected={d === day}
              className={
                d === day ? 'day-cal__tab day-cal__tab--on' : 'day-cal__tab'
              }
              onClick={() => setSelected(d)}
            >
              <span className="day-cal__tab-label">{dayLabel(d, baseToday)}</span>
              {n > 0 ? <span className="day-cal__tab-n">{n}</span> : null}
            </button>
          )
        })}
      </div>

      {allDay.length > 0 ? (
        <div className="day-cal__allday">
          {allDay.map((ev) => {
            const title = (ev.title || '').trim() || '(sin título)'
            return (
              <div key={String(ev.id)} className="day-cal__allday-card">
                <EventTitle
                  ev={ev}
                  title={title}
                  className="day-cal__allday-title"
                />
                <EventActions
                  ev={ev}
                  busyId={busyId}
                  busyKind={busyKind}
                  onToTask={onToTask}
                  onPrep={onPrep}
                />
              </div>
            )
          })}
        </div>
      ) : null}

      {timed.length === 0 ? (
        <p className="day-cal__empty muted">
          {allDay.length > 0 ? 'Sin horas fijas este día' : 'Nada este día'}
        </p>
      ) : (
        <div className="day-cal__grid" style={{ height: hours.length * HOUR_PX }}>
          <div className="day-cal__hours" aria-hidden>
            {hours.map((h) => (
              <div
                key={h}
                className="day-cal__hour"
                style={{ height: HOUR_PX }}
              >
                <span>{`${String(h).padStart(2, '0')}:00`}</span>
              </div>
            ))}
          </div>
          <div className="day-cal__lane">
            {hours.map((h) => (
              <div
                key={h}
                className="day-cal__line"
                style={{ top: ((h * 60 - rangeStart) / 60) * HOUR_PX }}
              />
            ))}
            {nowTop != null ? (
              <div
                className="day-cal__now"
                style={{ top: nowTop }}
                aria-label="Ahora"
              />
            ) : null}
            {laid.map((item) => {
              const width = `calc((100% - 0.4rem) / ${item.cols})`
              const left = `calc(${item.col} * (100% - 0.4rem) / ${item.cols} + 0.15rem)`
              const title = (item.ev.title || '').trim() || '(sin título)'
              const tip = `${title} · ${item.startLabel}–${item.endLabel}`
              const cls = [
                'day-cal__ev',
                item.ev.source === 'local'
                  ? 'day-cal__ev--local'
                  : 'day-cal__ev--google',
                item.short ? 'day-cal__ev--short' : '',
              ]
                .filter(Boolean)
                .join(' ')
              return (
                <div
                  key={String(item.ev.id)}
                  className={cls}
                  style={{
                    top: item.top,
                    height: item.height,
                    width,
                    left,
                  }}
                  title={tip}
                >
                  <div className="day-cal__ev-main">
                    {item.short ? (
                      <span className="day-cal__ev-line">
                        <span className="day-cal__ev-time">{item.startLabel}</span>
                        <EventTitle
                          ev={item.ev}
                          title={title}
                          className="day-cal__ev-title"
                        />
                      </span>
                    ) : (
                      <>
                        <EventTitle
                          ev={item.ev}
                          title={title}
                          className="day-cal__ev-title"
                        />
                        <span className="day-cal__ev-time">
                          {item.startLabel}–{item.endLabel}
                        </span>
                      </>
                    )}
                  </div>
                  <EventActions
                    ev={item.ev}
                    busyId={busyId}
                    busyKind={busyKind}
                    onToTask={onToTask}
                    onPrep={onPrep}
                  />
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
