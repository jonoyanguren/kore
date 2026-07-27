import { useState } from 'react'
import type { FormEvent } from 'react'
import { apiLogin } from '../api'

type Props = {
  onSuccess: () => void
}

export function Login({ onSuccess }: Props) {
  const [secret, setSecret] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const ok = await apiLogin(secret.trim())
      if (!ok) {
        setError('Secret incorrecto')
        return
      }
      onSuccess()
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login">
      <h1>Kore</h1>
      <p>Consola — introduce el secret</p>
      <form onSubmit={onSubmit}>
        <input
          type="password"
          autoComplete="current-password"
          placeholder="CONSOLE_SECRET"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          required
        />
        <button type="submit" disabled={busy}>
          Entrar
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
    </main>
  )
}
