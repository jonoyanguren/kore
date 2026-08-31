import { useEffect, useState } from 'react'
import { apiUsage, type UsageInfo } from '../api'

export function UsageChip({ variant = 'chip' }: { variant?: 'chip' | 'block' }) {
  const [usage, setUsage] = useState<UsageInfo | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const u = await apiUsage()
        if (!cancelled) setUsage(u)
      } catch {
        if (!cancelled) setUsage(null)
      }
    }
    void load()
    const id = window.setInterval(() => void load(), 60_000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  if (!usage) {
    return variant === 'block' ? (
      <p className="muted more-drawer__usage-empty">Sin datos de gasto aún</p>
    ) : null
  }

  const unlimited = Boolean(usage.unlimited)
  const remainingPct = unlimited
    ? 100
    : Math.max(
        0,
        Math.round(
          usage.remaining_pct ?? 100 - usage.pct_used,
        ),
      )
  const pct = unlimited ? 0 : Math.round(usage.pct_used)
  const label = unlimited
    ? 'sin tope este mes'
    : `te queda ${remainingPct}% este mes`
  const title = unlimited
    ? 'Este mes sin tope configurado.'
    : `Te queda ${remainingPct}% del mes.`

  const hot = !unlimited && (usage.blocked || usage.pct_used >= 85)
  const warm = !unlimited && usage.pct_used >= 60
  const fill = unlimited ? 0 : Math.min(100, Math.max(0, usage.pct_used))

  return (
    <span
      className={
        'console__usage' +
        (variant === 'block' ? ' console__usage--block' : '') +
        (hot ? ' is-hot' : warm ? ' is-warm' : '')
      }
      title={title}
      aria-label={title}
    >
      <span className="console__usage-label">LLM</span>
      <span className="console__usage-meta">
        <span className="console__usage-text">{label}</span>
        {unlimited ? null : (
          <span
            className="console__usage-track"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={pct}
          >
            <span
              className="console__usage-fill"
              style={{ width: `${fill}%` }}
            />
          </span>
        )}
      </span>
    </span>
  )
}
