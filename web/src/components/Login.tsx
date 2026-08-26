import { useState } from 'react'
import type { FormEvent } from 'react'
import { apiLogin, apiRegister } from '../api'
import type { MeUser } from '../types'
import { useToast } from './Toasts'

type Mode = 'login' | 'register'

type Props = {
  onSuccess: (user: MeUser | null) => void
}

export function Login({ onSuccess }: Props) {
  const toast = useToast()
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [ownerName, setOwnerName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

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
      const user = await apiLogin(email.trim(), password)
      if (!user) {
        setError('Email o contraseña incorrectos')
        toast.err('Email o contraseña incorrectos')
        return
      }
      toast.ok('Dentro')
      onSuccess(user)
    } finally {
      setBusy(false)
    }
  }

  const isRegister = mode === 'register'

  return (
    <main className="login">
      <h1>Kore</h1>
      <p>{isRegister ? 'Crea tu cuenta — cada uno su espacio' : 'Entra a tu consola'}</p>
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
          setMode(isRegister ? 'login' : 'register')
          setError(null)
        }}
      >
        {isRegister ? 'Ya tengo cuenta' : 'Crear cuenta'}
      </button>
      {error ? <p className="error">{error}</p> : null}
    </main>
  )
}
