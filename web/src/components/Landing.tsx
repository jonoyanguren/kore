import { useEffect, useId, useState } from 'react'
import type { MeUser } from '../types'
import { Login } from './Login'
import '../Landing.css'

type Gate = 'login' | 'register' | null

type Props = {
  onSuccess: (user: MeUser | null) => void
}

export function Landing({ onSuccess }: Props) {
  const [gate, setGate] = useState<Gate>(null)
  const titleId = useId()

  useEffect(() => {
    const prevTitle = document.title
    document.title = 'Kore — tu día, en un sitio'
    const meta = document.querySelector('meta[name="theme-color"]')
    const prevTheme = meta?.getAttribute('content') ?? ''
    meta?.setAttribute('content', '#12151a')
    return () => {
      document.title = prevTitle
      if (meta) meta.setAttribute('content', prevTheme || '#1f6f5b')
    }
  }, [])

  useEffect(() => {
    if (!gate) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setGate(null)
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [gate])

  return (
    <div className="landing">
      <header className="lp-nav">
        <a className="lp-mark" href="#top">
          Kore
        </a>
        <div className="lp-nav__actions">
          <button
            type="button"
            className="lp-btn lp-btn--ghost lp-btn--sm"
            onClick={() => setGate('login')}
          >
            Entrar
          </button>
          <button
            type="button"
            className="lp-btn lp-btn--solid lp-btn--sm"
            onClick={() => setGate('register')}
          >
            Crear cuenta
          </button>
        </div>
      </header>

      <main id="top">
        <section className="lp-hero">
          <h1>
            Tu día,
            <br />
            en un sitio.
          </h1>
          <p className="lp-hero__sub">
            Briefing, correo, agenda y un companion con tu tono. Cada cuenta,
            su espacio.
          </p>
          <div className="lp-hero__cta">
            <button
              type="button"
              className="lp-btn lp-btn--solid"
              onClick={() => setGate('register')}
            >
              Crear cuenta
            </button>
            <button
              type="button"
              className="lp-btn lp-btn--ghost"
              onClick={() => setGate('login')}
            >
              Entrar
            </button>
          </div>
          <div className="lp-hero__stage">
            <div className="lp-hero__glow" />
            <DayMock />
          </div>
        </section>

        <section className="lp-band lp-band--paper">
          <div className="lp-band__copy">
            <p className="lp-kicker">Día</p>
            <h2>Despiertas. Ya está ordenado.</h2>
            <p>
              Una vista: el briefing de la mañana, lo que hay que hacer, el
              correo y el calendario. Sin saltar de app en app para saber qué
              toca.
            </p>
          </div>
          <CalMock />
        </section>

        <section className="lp-band lp-band--ink lp-band--flip">
          <div className="lp-band__copy">
            <p className="lp-kicker">Companion</p>
            <h2>El tuyo. No un genérico.</h2>
            <p>
              Eliges el nombre y cómo te habla. Directo, breve, o como tú
              quieras. Vive en tu consola — no es la voz de Kore.
            </p>
          </div>
          <ChatMock />
        </section>

        <section className="lp-band lp-band--paper">
          <div className="lp-band__copy">
            <p className="lp-kicker">Misiones</p>
            <h2>Lanzas. Sigues con tu día.</h2>
            <p>
              Un encargo, un loop, un resultado. Investiga o prepara mientras
              tú estás en otra cosa. Cuando acaba, el markdown está en tu
              espacio.
            </p>
          </div>
          <MissionsMock />
        </section>

        <section className="lp-close">
          <h2>Empieza en un minuto.</h2>
          <p>Email, contraseña, nombre del companion. Tu home, cerrado.</p>
          <button
            type="button"
            className="lp-btn lp-btn--solid"
            onClick={() => setGate('register')}
          >
            Crear cuenta
          </button>
        </section>
      </main>

      <footer className="lp-foot">
        <span>Kore</span>
        <span>Cada cuenta, su espacio.</span>
      </footer>

      {gate ? (
        <div
          className="lp-gate"
          role="presentation"
          onClick={() => setGate(null)}
        >
          <div
            className="lp-gate__card"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="lp-gate__head">
              <h2 id={titleId} className="lp-gate__title">
                {gate === 'register' ? 'Crea tu cuenta' : 'Entra'}
              </h2>
              <button
                type="button"
                className="lp-gate__x"
                onClick={() => setGate(null)}
                aria-label="Cerrar"
              >
                ×
              </button>
            </div>
            <Login
              onSuccess={onSuccess}
              initialMode={gate}
              onModeChange={setGate}
              embedded
            />
          </div>
        </div>
      ) : null}
    </div>
  )
}

function DayMock() {
  return (
    <div className="lp-device" aria-hidden>
      <div className="lp-device__chrome">
        <span className="lp-device__dots">
          <i />
          <i />
          <i />
        </span>
        <span className="lp-device__url">kore.fly.dev</span>
      </div>
      <div className="lp-device__nav">
        <strong>Kore</strong>
        <span className="is-on">Día</span>
        <span>Chat</span>
        <span>Board</span>
        <span>Misiones</span>
      </div>
      <div className="lp-day">
        <p className="lp-day__date">jueves 27 ago</p>
        <p className="lp-day__clock">09:41</p>
        <p className="lp-day__quote">
          Lo importante es no dejar de preguntar.
        </p>
        <div className="lp-day__grid">
          <div>
            <h3>Hoy</h3>
            <ul>
              <li>
                Call con Marta
                <em>11:00</em>
              </li>
              <li>
                Enviar propuesta
                <em>hoy</em>
              </li>
              <li>
                Gym
                <em>16:00</em>
              </li>
            </ul>
          </div>
          <div>
            <h3>Inbox</h3>
            <ul>
              <li>
                Luis · contrato v3
                <em>2h</em>
              </li>
              <li>
                Ana · fechas offsite
                <em>ayer</em>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

function CalMock() {
  return (
    <div className="lp-cal" aria-hidden>
      <div className="lp-cal__row lp-cal__row--now">
        <span>11:00</span>
        <strong>Call con Marta</strong>
        <em>30 min</em>
      </div>
      <div className="lp-cal__row">
        <span>14:30</span>
        <strong>Revisión propuesta</strong>
        <em>45 min</em>
      </div>
      <div className="lp-cal__row">
        <span>16:00</span>
        <strong>Gym</strong>
        <em>1 h</em>
      </div>
    </div>
  )
}

function ChatMock() {
  return (
    <div className="lp-chat" aria-hidden>
      <div className="lp-chat__you">Mara, ¿qué tengo a las 11?</div>
      <div className="lp-chat__her">
        Call con Marta, 30 min. El prep está en el calendario. ¿Te abro el
        brief?
      </div>
    </div>
  )
}

function MissionsMock() {
  return (
    <div className="lp-mis" aria-hidden>
      <div className="lp-mis__row">
        <i className="lp-mis__dot lp-mis__dot--done" />
        <strong>Informe competencia</strong>
        <em>listo</em>
      </div>
      <div className="lp-mis__row">
        <i className="lp-mis__dot lp-mis__dot--run" />
        <strong>Prep entrevista</strong>
        <em>en curso</em>
      </div>
      <div className="lp-mis__row">
        <i className="lp-mis__dot" />
        <strong>Brief del viaje</strong>
        <em>en cola</em>
      </div>
    </div>
  )
}
