import { useEffect, useState } from 'react'
import { apiUsage, type UsageInfo } from '../api'

function formatUsd(n: number): string {
  if (n >= 100) return `$${n.toFixed(0)}`
  if (n >= 10) return `$${n.toFixed(1)}`
  return `$${n.toFixed(2)}`
}

export function UsageChip() {
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

  if (!usage) return null

  const label = `${formatUsd(usage.usage_usd)} · ${Math.round(usage.pct_used)}%`
  const title =
    `OpenRouter: ${formatUsd(usage.usage_usd)} usados de ` +
    `${formatUsd(usage.total_usd)} (${usage.pct_used.toFixed(1)}%). ` +
    `Quedan ${formatUsd(usage.remaining_usd)}.`

  const hot = usage.pct_used >= 85
  const warm = usage.pct_used >= 60

  return (
    <span
      className={
        'console__usage' +
        (hot ? ' is-hot' : warm ? ' is-warm' : '')
      }
      title={title}
      aria-label={title}
    >
      {label}
    </span>
  )
}
