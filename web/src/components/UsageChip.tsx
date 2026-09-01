import { useEffect, useState } from 'react'
import { apiUsage, type UsageInfo } from '../api'

function usd(n: number): string {
  if (n < 0.01) return `$${n.toFixed(4)}`
  return `$${n.toFixed(2)}`
}

function HomeChip({ usage, variant }: { usage: UsageInfo; variant: 'chip' | 'block' }) {
  const unlimited = Boolean(usage.unlimited)
  const remainingPct = unlimited
    ? 100
    : Math.max(0, Math.round(usage.remaining_pct ?? 100 - usage.pct_used))
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
            <span className="console__usage-fill" style={{ width: `${fill}%` }} />
          </span>
        )}
      </span>
    </span>
  )
}

function ProviderChip({
  provider,
  variant,
}: {
  provider: UsageInfo
  variant: 'chip' | 'block'
}) {
  const remaining = provider.remaining_usd
  const monthly = provider.usage_monthly_usd ?? 0
  let label: string
  let title: string
  if (remaining != null) {
    label = `quedan ${usd(remaining)} en OpenRouter`
    title = `Saldo de la API key (cuenta compartida). Este mes ${usd(monthly)}.`
  } else if (provider.unlimited) {
    label =
      monthly > 0
        ? `${usd(monthly)} este mes · key sin tope`
        : 'key OpenRouter sin tope'
    title = 'La key no tiene límite de crédito. El saldo de cuenta no está visible.'
  } else {
    label = `gastados ${usd(provider.usage_usd)}`
    title = 'OpenRouter no devolvió el saldo restante.'
  }
  const hot = remaining != null && remaining <= 1
  const warm = remaining != null && remaining <= 5
  const fill =
    remaining != null && provider.total_usd > 0
      ? Math.min(100, Math.max(0, provider.pct_used))
      : 0

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
      <span className="console__usage-label">Key</span>
      <span className="console__usage-meta">
        <span className="console__usage-text">{label}</span>
        {fill > 0 ? (
          <span
            className="console__usage-track"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(provider.pct_used)}
          >
            <span className="console__usage-fill" style={{ width: `${fill}%` }} />
          </span>
        ) : null}
      </span>
    </span>
  )
}

export function UsageChip({ variant = 'chip' }: { variant?: 'chip' | 'block' }) {
  const [usage, setUsage] = useState<UsageInfo | null>(null)
  const [provider, setProvider] = useState<UsageInfo | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const data = await apiUsage()
        if (cancelled) return
        setUsage(data.usage)
        setProvider(data.provider)
      } catch {
        if (!cancelled) {
          setUsage(null)
          setProvider(null)
        }
      }
    }
    void load()
    const id = window.setInterval(() => void load(), 60_000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  if (!usage && !provider) {
    return variant === 'block' ? (
      <p className="muted more-drawer__usage-empty">Sin datos de gasto aún</p>
    ) : null
  }

  return (
    <div className={variant === 'block' ? 'console__usage-stack' : undefined}>
      {usage ? <HomeChip usage={usage} variant={variant} /> : null}
      {provider ? <ProviderChip provider={provider} variant={variant} /> : null}
    </div>
  )
}
