import { useEffect, useState } from 'react'
import {
  apiMe,
  apiUsage,
  llmCapCopy,
  LLM_CAP_EVENT,
  openMoreMes,
} from '../api'
import type { BillingInfo } from '../types'
import { useToast } from './Toasts'

type Props = {
  variant?: 'banner' | 'inline'
  /** When true, always show (caller already knows it's a cap error). */
  force?: boolean
}

export function LlmCapCta({ variant = 'inline', force = false }: Props) {
  const toast = useToast()
  const [billing, setBilling] = useState<BillingInfo | null>(null)
  const [blocked, setBlocked] = useState(force)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [me, usage] = await Promise.all([apiMe(), apiUsage()])
        if (cancelled) return
        setBilling(me?.billing ?? null)
        if (usage.usage?.blocked) setBlocked(true)
      } catch {
        /* ignore */
      }
    }
    void load()
    function onCap() {
      setBlocked(true)
      void load()
    }
    window.addEventListener(LLM_CAP_EVENT, onCap)
    return () => {
      cancelled = true
      window.removeEventListener(LLM_CAP_EVENT, onCap)
    }
  }, [])

  if (!force && !blocked) return null

  const copy = llmCapCopy(billing)
  const canUpgrade = Boolean(billing?.upgrade || billing?.has_customer)

  async function go() {
    if (busy) return
    setBusy(true)
    const r = await openMoreMes(billing)
    setBusy(false)
    if (r.ok) return
    if (r.none) {
      toast.err('Este mes no da para más. Vuelve el día 1.')
      return
    }
    toast.err('No se pudo abrir el pago.')
  }

  return (
    <div
      className={
        'cap-cta' + (variant === 'banner' ? ' cap-cta--banner' : '')
      }
      role="status"
    >
      <p className="cap-cta__text">{copy}</p>
      {canUpgrade ? (
        <button
          type="button"
          className="cap-cta__btn"
          disabled={busy}
          onClick={() => void go()}
        >
          {busy ? 'Abriendo…' : 'Más mes'}
        </button>
      ) : null}
    </div>
  )
}
