import { useEffect, useState } from 'react'
import { apiBillingCheckout } from '../api'
import type { MeUser } from '../types'
import { PricingTable, type PlanId } from './PricingTable'
import '../Landing.css'

type Props = {
  user: MeUser
}

export function Paywall({ user }: Props) {
  const [busy, setBusy] = useState<PlanId | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const prevTitle = document.title
    document.title = 'Kore — elige plan'
    return () => {
      document.title = prevTitle
    }
  }, [])

  async function pick(id: PlanId) {
    setBusy(id)
    setError(null)
    const r = await apiBillingCheckout(id)
    setBusy(null)
    if (!r.ok) {
      setError(
        r.status === 503
          ? 'El pago aún no está activo. Prueba en un rato.'
          : 'No se pudo abrir el pago.',
      )
      return
    }
    window.location.href = r.url
  }

  return (
    <main className="landing">
      <section className="lp-price lp-price--paywall" id="precio">
        <p className="lp-kicker">Precio</p>
        <h2>5 € abre. 10 y 20 son más mes.</h2>
        <p>
          Hola {user.owner_name || 'tú'}. Elige plan. Stripe avisa a Kore; si
          tardas un segundo en entrar, espera y recarga.
        </p>
        <PricingTable
          cta={(plan) => `Pagar ${plan.eur} €`}
          onPick={(id) => void pick(id)}
          busy={busy}
        />
        {error ? <p className="lp-price__err">{error}</p> : null}
      </section>
    </main>
  )
}
