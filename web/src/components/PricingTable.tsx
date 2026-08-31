export type PlanId = '5' | '10' | '20'

export type Plan = {
  id: PlanId
  eur: number
  name: string
  blurb: string
  use: string
  featured: boolean
}

export const PLANS: Plan[] = [
  {
    id: '5',
    eur: 5,
    name: 'Entrar',
    blurb: 'El mes contenido.',
    use: 'Uso diario, para el Día, un par de correos y un chat. Una misión, si entra.',
    featured: false,
  },
  {
    id: '10',
    eur: 10,
    name: 'Más',
    blurb: 'Lo mismo, con más mes.',
    use: 'Uso diario, para el Día, correo y chat cada día. Unas pocas misiones.',
    featured: true,
  },
  {
    id: '20',
    eur: 20,
    name: 'Holgado',
    blurb: 'Por si este mes aprietas.',
    use: 'Uso diario, para el Día, correo, chat y varias misiones.',
    featured: false,
  },
]

type Props = {
  cta: (plan: Plan) => string
  onPick: (id: PlanId) => void
  busy?: PlanId | null
  disabled?: boolean
}

export function PricingTable({ cta, onPick, busy = null, disabled }: Props) {
  return (
    <div className="lp-plans">
      {PLANS.map((plan) => (
        <article
          key={plan.id}
          className={
            'lp-plan' + (plan.featured ? ' lp-plan--featured' : '')
          }
        >
          {plan.featured ? <p className="lp-plan__tag">El de en medio</p> : null}
          <p className="lp-plan__name">{plan.name}</p>
          <p className="lp-plan__price">
            {plan.eur} €<span> / mes</span>
          </p>
          <p className="lp-plan__blurb">{plan.blurb}</p>
          <p className="lp-plan__use">{plan.use}</p>
          <button
            type="button"
            className={
              'lp-btn lp-btn--sm' +
              (plan.featured ? ' lp-btn--solid' : ' lp-btn--ghost')
            }
            disabled={disabled || busy !== null}
            onClick={() => onPick(plan.id)}
          >
            {busy === plan.id ? 'Abriendo…' : cta(plan)}
          </button>
        </article>
      ))}
    </div>
  )
}
