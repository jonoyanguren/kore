import { useState } from 'react'
import type { FormEvent } from 'react'
import { apiSaveCompanion } from '../api'
import type { MeUser } from '../types'
import { useToast } from './Toasts'

type Props = {
  user: MeUser
  onDone: (user: MeUser) => void
}

export function Onboarding({ user, onDone }: Props) {
  const toast = useToast()
  const [ownerName, setOwnerName] = useState(user.owner_name)
  const [companionName, setCompanionName] = useState(user.companion_name || '')
  const [tone, setTone] = useState(user.companion_tone || '')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const saved = await apiSaveCompanion({
        owner_name: ownerName.trim(),
        companion_name: companionName.trim(),
        companion_tone: tone.trim(),
      })
      if (!saved) {
        setError('No se pudo guardar')
        toast.err('No se pudo guardar')
        return
      }
      toast.ok('Listo')
      onDone(saved)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login login--wide">
      <h1>¿Cómo te llamo?</h1>
      <p>Elige el nombre del companion y cómo quieres que te hable. Luego puedes cambiarlo.</p>
      <form onSubmit={onSubmit}>
        <label>
          Tu nombre
          <input
            type="text"
            autoComplete="name"
            value={ownerName}
            onChange={(e) => setOwnerName(e.target.value)}
            required
          />
        </label>
        <label>
          Nombre del companion
          <input
            type="text"
            placeholder="Jone, Mara, Otto…"
            value={companionName}
            onChange={(e) => setCompanionName(e.target.value)}
            required
          />
        </label>
        <label>
          Tono
          <textarea
            placeholder="Directo, breve, sin relleno. Me tutea. Si no sabe algo, lo dice."
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            required
            minLength={8}
          />
        </label>
        <button type="submit" disabled={busy}>
          Empezar
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
    </main>
  )
}
