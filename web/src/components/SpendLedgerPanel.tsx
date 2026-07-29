import { useEffect, useState } from 'react'
import { apiSpend, type SpendLedger } from '../api'

const KIND_LABEL: Record<string, string> = {
  chat: 'Chat',
  mission: 'Misión',
  dream: 'Dream',
  clarify: 'Aclarar',
  gmail: 'Gmail',
  transcribe: 'Voz',
  other: 'Otro',
}

function formatUsd(usd: number, estimated = false): string {
  if (usd <= 0) return '$0.00'
  let text: string
  if (usd < 0.01) text = `$${usd.toFixed(4)}`
  else if (usd < 1) text = `$${usd.toFixed(3)}`
  else text = `$${usd.toFixed(2)}`
  return estimated ? `~${text}` : text
}

function shortModel(model: string): string {
  const parts = model.split('/')
  return parts[parts.length - 1] || model
}

function timeLabel(iso: string): string {
  // SQLite datetime('now') is UTC-ish; show HH:MM if parseable
  const m = iso.match(/(\d{2}):(\d{2})/)
  return m ? `${m[1]}:${m[2]}` : iso.slice(0, 16)
}

export function SpendLedgerPanel() {
  const [data, setData] = useState<SpendLedger | null>(null)
  const [err, setErr] = useState(false)

  useEffect(() => {
    let cancelled = false
    void apiSpend(7).then((d) => {
      if (cancelled) return
      if (!d) setErr(true)
      else setData(d)
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (err) {
    return <p className="muted more-drawer__usage-empty">Sin ledger aún</p>
  }
  if (!data) {
    return <p className="muted more-drawer__usage-empty">…</p>
  }

  const { summary, events, today_usd } = data

  return (
    <div className="spend-ledger">
      <div className="spend-ledger__totals">
        <div>
          <span className="muted">Hoy</span>
          <strong>{formatUsd(today_usd)}</strong>
        </div>
        <div>
          <span className="muted">7 días</span>
          <strong>{formatUsd(summary.usd)}</strong>
        </div>
        <div>
          <span className="muted">Llamadas</span>
          <strong>{summary.calls}</strong>
        </div>
      </div>

      {summary.by_kind.length > 0 ? (
        <ul className="spend-ledger__kinds">
          {summary.by_kind.map((k) => (
            <li key={k.kind}>
              <span>{KIND_LABEL[k.kind] || k.kind}</span>
              <span className="muted">
                {formatUsd(k.usd)} · {k.calls}
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      {events.length === 0 ? (
        <p className="muted more-drawer__usage-empty">
          Aún no hay filas. Chat, dream y misiones irán apareciendo aquí.
        </p>
      ) : (
        <ul className="spend-ledger__events">
          {events.slice(0, 40).map((e) => (
            <li key={e.id}>
              <span className="spend-ledger__when muted">
                {e.day.slice(5)} {timeLabel(e.created_at)}
              </span>
              <span className="spend-ledger__kind">
                {KIND_LABEL[e.kind] || e.kind}
              </span>
              <span className="spend-ledger__usd">
                {formatUsd(e.usd, e.estimated)}
              </span>
              <span className="spend-ledger__model muted" title={e.model}>
                {shortModel(e.model)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
