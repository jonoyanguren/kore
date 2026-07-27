/** Relative Spanish labels from ISO / SQLite UTC timestamps. */
export function formatRelativeEs(createdAt: string, now = new Date()): string {
  const raw = (createdAt || '').trim()
  if (!raw) return ''
  let then: Date
  try {
    // SQLite datetime('now') → treat as UTC
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(raw) && !raw.includes('T')) {
      then = new Date(raw.replace(' ', 'T') + 'Z')
    } else {
      then = new Date(raw.endsWith('Z') || raw.includes('+') ? raw : raw + 'Z')
    }
    if (Number.isNaN(then.getTime())) return raw.slice(0, 16)
  } catch {
    return raw.slice(0, 16)
  }

  const secs = Math.max(0, Math.floor((now.getTime() - then.getTime()) / 1000))
  if (secs < 90) return 'hace un momento'
  const mins = Math.floor(secs / 60)
  if (mins < 50) return mins === 1 ? 'hace un minuto' : `hace ${mins} minutos`
  const hours = Math.floor(secs / 3600)

  const madridDay = (d: Date) =>
    new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Europe/Madrid',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(d)

  const today = madridDay(now)
  const thenDay = madridDay(then)
  if (hours < 24 && today === thenDay) {
    return hours <= 1 ? 'hace una hora' : `hace ${hours} horas`
  }

  const dayMs = 24 * 3600 * 1000
  // Approximate calendar days via Madrid midnight-ish using formatted dates
  const [ty, tm, td] = today.split('-').map(Number)
  const [yy, ym, yd] = thenDay.split('-').map(Number)
  const days = Math.round(
    (Date.UTC(ty, tm - 1, td) - Date.UTC(yy, ym - 1, yd)) / dayMs,
  )
  if (days === 1) return 'ayer'
  if (days === 2) return 'hace un día'
  if (days > 0 && days < 7) {
    const wd = new Intl.DateTimeFormat('es-ES', {
      timeZone: 'Europe/Madrid',
      weekday: 'long',
    }).format(then)
    return `el ${wd}`
  }
  const label = new Intl.DateTimeFormat('es-ES', {
    timeZone: 'Europe/Madrid',
    day: 'numeric',
    month: 'long',
    ...(yy !== ty ? { year: 'numeric' as const } : {}),
  }).format(then)
  return label
}
