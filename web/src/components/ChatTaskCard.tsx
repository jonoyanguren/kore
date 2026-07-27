import type { Task } from '../types'

const STATUS_ES: Record<string, string> = {
  open: 'abierta',
  in_progress: 'en curso',
  done: 'hecha',
  cancelled: 'cancelada',
}

type Props = {
  task: Task
  onComplete?: (id: number) => void
}

export function ChatTaskCard({ task, onComplete }: Props) {
  return (
    <div className="chat-task">
      <div className="chat-task__title">
        <strong>
          {task.id}. {task.title}
        </strong>
        {onComplete && task.status !== 'done' && task.status !== 'cancelled' ? (
          <button
            type="button"
            className="chat-task__done"
            title="Marcar hecha"
            onClick={() => onComplete(task.id)}
          >
            ✓
          </button>
        ) : null}
      </div>
      <div className="chat-task__meta">
        <span>{STATUS_ES[task.status] ?? task.status}</span>
        {task.project ? <span>{task.project}</span> : null}
        {task.due_at ? <span>{task.due_at}</span> : null}
      </div>
      {task.url ? (
        <a href={task.url} target="_blank" rel="noreferrer">
          {task.url.replace(/^https?:\/\//, '').slice(0, 40)}
        </a>
      ) : null}
    </div>
  )
}
