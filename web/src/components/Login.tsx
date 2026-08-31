import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { apiLogin, apiRegister } from '../api'
import type { MeUser } from '../types'
import { useToast } from './Toasts'

type Mode = 'login' | 'register'

type Props = {
  onSuccess: (user: MeUser | null) => void
  initialMode?: Mode
  embedded?: boolean
  onModeChange?: (mode: Mode) => void
}

export function Login({
  onSuccess,
  initialMode = 'login',
  embedded = false,
  onModeChange,
}: Props) {
  const toast = useToast()
  const [mode, setMode] = useState<Mode>(initialMode)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [ownerName, setOwnerName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setMode(initialMode)
  }, [initialMode])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      if (mode === 'register') {
        const result = await apiRegister(email.trim(), password, ownerName.trim())
        if (!result.ok) {
          const msg = result.detail || 'No se pudo crear la cuenta'
          setError(msg)
          toast.err(msg)
          return
        }
        toast.ok('Cuenta creada')
        onSuccess(result.user)
        return
      }
      const result = await apiLogin(email.trim(), password)
      if (!result.ok || !result.user) {
        const msg =
          result.ok === false && result.detail
            ? result.detail
            : 'Email o contraseña incorrectos'
        setError(msg)
        toast.err(msg)
        return
      }
      toast.ok('Dentro')
      onSuccess(result.user)
    } finally {
      setBusy(false)
    }
  }

  const isRegister = mode === 'register'

  return (
    <div className="login">
      {embedded ? null : <h1>Kore</h1>}
      <p>
        {isRegister
          ? 'El piloto es por invitación. Usa el email al que te escribimos.'
          : 'Entra a tu consola'}
      </p>
      <form onSubmit={onSubmit}>
        {isRegister ? (
          <label>
            Tu nombre
            <input
              type="text"
              autoComplete="name"
              placeholder="Ana"
              value={ownerName}
              onChange={(e) => setOwnerName(e.target.value)}
              required
              autoFocus={embedded}
            />
          </label>
        ) : null}
        <label>
          Email
          <input
            type="email"
            autoComplete="email"
            placeholder="tu@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus={embedded && !isRegister}
          />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            placeholder="mínimo 8 caracteres"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>
        <button type="submit" disabled={busy}>
          {isRegister ? 'Crear cuenta' : 'Entrar'}
        </button>
      </form>
      <button
        type="button"
        className="ghost login__switch"
        onClick={() => {
          const next = isRegister ? 'login' : 'register'
          setMode(next)
          onModeChange?.(next)
          setError(null)
        }}
      >
        {isRegister ? 'Ya tengo cuenta' : 'Tengo invitación'}
      </button>
      {error ? <p className="error">{error}</p> : null}
    </div>
  )
}
