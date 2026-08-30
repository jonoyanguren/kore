import type { VoiceProfile } from '../types'

export const DEFAULT_VOICE: VoiceProfile = {
  address: 'tu',
  length: 'corto',
  warmth: 'directo',
  humor: 'seco',
  signoff: 'nombre',
  notes: '',
}

type Group = {
  key: keyof Omit<VoiceProfile, 'notes'>
  label: string
  options: { id: string; label: string }[]
}

const GROUPS: Group[] = [
  {
    key: 'address',
    label: 'Trato',
    options: [
      { id: 'tu', label: 'Tú' },
      { id: 'usted', label: 'Usted' },
      { id: 'da_igual', label: 'Da igual' },
    ],
  },
  {
    key: 'length',
    label: 'Largo',
    options: [
      { id: 'telegrafico', label: 'Telegráfico' },
      { id: 'corto', label: 'Corto' },
      { id: 'normal', label: 'Normal' },
    ],
  },
  {
    key: 'warmth',
    label: 'Calidez',
    options: [
      { id: 'directo', label: 'Directo' },
      { id: 'neutro', label: 'Neutro' },
      { id: 'cercano', label: 'Cercano' },
    ],
  },
  {
    key: 'humor',
    label: 'Humor',
    options: [
      { id: 'cero', label: 'Cero' },
      { id: 'seco', label: 'Seco' },
      { id: 'si', label: 'Un poco' },
    ],
  },
  {
    key: 'signoff',
    label: 'Firma del mail',
    options: [
      { id: 'nada', label: 'Nada' },
      { id: 'nombre', label: 'Tu nombre' },
      { id: 'saludo', label: 'Un saludo + nombre' },
    ],
  },
]

type Props = {
  value: VoiceProfile
  onChange: (next: VoiceProfile) => void
  notesPlaceholder?: string
}

export function VoiceForm({ value, onChange, notesPlaceholder }: Props) {
  return (
    <div className="voice-form">
      {GROUPS.map((g) => (
        <div key={g.key} className="voice-form__row">
          <p className="voice-form__label">{g.label}</p>
          <div className="voice-form__chips" role="group" aria-label={g.label}>
            {g.options.map((opt) => {
              const active = value[g.key] === opt.id
              return (
                <button
                  key={opt.id}
                  type="button"
                  className={
                    'voice-form__chip' + (active ? ' is-active' : '')
                  }
                  aria-pressed={active}
                  onClick={() => onChange({ ...value, [g.key]: opt.id })}
                >
                  {opt.label}
                </button>
              )
            })}
          </div>
        </div>
      ))}
      <label className="voice-form__notes">
        Algo más
        <input
          type="text"
          maxLength={400}
          value={value.notes}
          placeholder={notesPlaceholder || 'Opcional. Una línea.'}
          onChange={(e) => onChange({ ...value, notes: e.target.value })}
        />
      </label>
    </div>
  )
}
