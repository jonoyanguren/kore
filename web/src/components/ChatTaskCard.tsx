import { formatWhen } from '../dates'
import { copyToClipboard, shortUrlLabel } from '../lib/clipboard'
import type { Task } from '../types'
import { ProjectChip } from './ProjectChip'
import { useToast } from './Toasts'

const STATUS_ES: Record<string, string> = {
  open: 'abierta',
  in_progress: 'en curso',
  done: 'hecha',
  cancelled: 'cancelada',
}

type Props = {
  task: Task
  onOpen?: (task: Task) => void
  onComplete?: (id: number) => void
  onStart?: (id: number) => void
}

export function ChatTaskCard({ task, onOpen, onComplete, onStart }: Props) {
  const toast = useToast()
  const canAct = task.status !== 'done' && task.status !== 'cancelled'

  async function onCopyUrl() {
    const ok = await copyToClipboard(task.url || '')
    if (ok) toast.ok('Copiado')
    else toast.err('No se pudo copiar')
  }

  return (
    <div className="chat-task">
      <div className="chat-task__title">
        <strong>
          {task.id}. {task.title}
        </strong>
      </div>
      <div className="chat-task__meta">
        <span>{STATUS_ES[task.status] ?? task.status}</span>
        <ProjectChip project={task.project} />
        {task.due_at ? <span>{formatWhen(task.due_at)}</span> : null}
      </div>
      {task.url ? (
        <div className="chat-task__url">
          <a href={task.url} target="_blank" rel="noreferrer" title={task.url}>
            {shortUrlLabel(task.url, 40)}
          </a>
          <button
            type="button"
            className="chat-task__btn"
            title="Copiar URL"
            onClick={() => void onCopyUrl()}
          >
            Copiar
          </button>
        </div>
      ) : null}
      <div className="chat-task__actions">
        {onOpen ? (
          <button type="button" className="chat-task__btn" onClick={() => onOpen(task)}>
            Abrir
          </button>
        ) : null}
        {onStart && canAct && task.status !== 'in_progress' ? (
          <button
            type="button"
            className="chat-task__btn"
            onClick={() => onStart(task.id)}
          >
            En curso
          </button>
        ) : null}
        {onComplete && canAct ? (
          <button
            type="button"
            className="chat-task__btn chat-task__btn--done"
            onClick={() => onComplete(task.id)}
          >
            Hecha
          </button>
        ) : null}
      </div>
    </div>
  )
}
