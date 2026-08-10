import { useState } from 'react'
import {
  apiCreateCalendarEvent,
  type CalendarProposal,
} from '../api'
import { useToast } from './Toasts'

type Props = {
  proposal: CalendarProposal
  onDone: () => void
  onCancel: () => void
  onCreated: () => void
}

export function ChatCalendarProposalCard({
  proposal,
  onDone,
  onCancel,
  onCreated,
}: Props) {
  const toast = useToast()
  const [title, setTitle] = useState(proposal.title)
  const [startsAt, setStartsAt] = useState(proposal.starts_at)
  const [endsAt, setEndsAt] = useState(proposal.ends_at)
  const [busy, setBusy] = useState(false)
  const canWrite = proposal.can_write !== false
  const conflicts = proposal.conflicts ?? []

  async function onCreate() {
    if (busy) return
    if (!canWrite) {
      toast.err('Reconecta en Más → Gmail para crear eventos')
      return
    }
    setBusy(true)
    try {
      await apiCreateCalendarEvent({
        title: title.trim(),
        starts_at: startsAt.trim(),
        ends_at: endsAt.trim(),
        description: proposal.description || '',
      })
      toast.ok('Bloque creado en Calendar')
      onCreated()
      onDone()
    } catch (err) {
      toast.err(String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="chat-cal-proposal">
      <div className="chat-cal-proposal__head">Crear en Calendar</div>
      {proposal.reason ? (
        <p className="chat-cal-proposal__reason muted">{proposal.reason}</p>
      ) : null}
      <label className="chat-cal-proposal__field">
        <span>Título</span>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={busy}
          maxLength={200}
        />
      </label>
      <div className="chat-cal-proposal__times">
        <label className="chat-cal-proposal__field">
          <span>Inicio</span>
          <input
            value={startsAt}
            onChange={(e) => setStartsAt(e.target.value)}
            disabled={busy}
            placeholder="YYYY-MM-DDTHH:MM"
          />
        </label>
        <label className="chat-cal-proposal__field">
          <span>Fin</span>
          <input
            value={endsAt}
            onChange={(e) => setEndsAt(e.target.value)}
            disabled={busy}
            placeholder="YYYY-MM-DDTHH:MM"
          />
        </label>
      </div>
      {conflicts.length > 0 ? (
        <div className="chat-cal-proposal__conflicts">
          <p>Posible solape:</p>
          <ul>
            {conflicts.map((c) => (
              <li key={`${c.starts_at}-${c.title}`}>
                {c.starts_at} — {c.title}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {!canWrite ? (
        <p className="chat-cal-proposal__warn">
          Falta permiso write.{' '}
          <a href="/api/gmail/connect">Reconectar Google</a>
        </p>
      ) : null}
      <div className="chat-cal-proposal__actions">
        <button
          type="button"
          className="chat-task__btn"
          disabled={busy}
          onClick={onCancel}
        >
          Cancelar
        </button>
        <button
          type="button"
          className="chat-task__btn chat-task__btn--done"
          disabled={busy || !title.trim() || !canWrite}
          onClick={() => void onCreate()}
        >
          {busy ? 'Creando…' : 'Crear'}
        </button>
      </div>
    </div>
  )
}
