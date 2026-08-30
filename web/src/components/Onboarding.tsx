import { useState } from 'react'
import type { FormEvent } from 'react'
import { apiSaveCompanion } from '../api'
import type { MeUser } from '../types'
import { useToast } from './Toasts'
import { DEFAULT_VOICE, VoiceForm } from './VoiceForm'

type Props = {
  user: MeUser
  onDone: (user: MeUser) => void
}

export function Onboarding({ user, onDone }: Props) {
  const toast = useToast()
  const [ownerName, setOwnerName] = useState(user.owner_name)
  const [companionName, setCompanionName] = useState(user.companion_name || '')
  const [voice, setVoice] = useState(user.voice || DEFAULT_VOICE)
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
        voice,
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
    <main className="gate">
      <div className="gate__card login login--wide login--voice">
        <h1>¿Cómo te llamo?</h1>
        <p>
          Nombre, el del companion, y cómo quieres que te hable — también en el
          mail. Luego lo cambias en Más o con <code>/tono</code>.
        </p>
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
          <VoiceForm value={voice} onChange={setVoice} />
          <button type="submit" disabled={busy}>
            Empezar
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
      </div>
    </main>
  )
}
