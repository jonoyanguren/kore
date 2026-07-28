/** Human dates for Board / Día (Europe/Madrid calendar). */

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

function madridTodayIso(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Europe/Madrid' })
}

/** Format due_at / agenda starts_at for UI (hoy / mañana / 28-Jul · time). */
export function formatWhen(raw: string | null | undefined): string {
  if (!raw) return ''
  const m = raw.match(/T(\d{2}:\d{2})/)
  const day = raw.slice(0, 10)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return raw
  const today = madridTodayIso()
  // All-day / date-only often land as T00:00 — don't show midnight.
  const time = m && m[1] !== '00:00' ? m[1] : ''

  if (day === today) return time ? `hoy ${time}` : 'hoy'

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
