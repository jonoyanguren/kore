import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { formatWhen } from '../dates'
import { copyToClipboard } from '../lib/clipboard'
import type { Task } from '../types'
import { ProjectChip } from './ProjectChip'
import { useToast } from './Toasts'

type Props = {
  task: Task
  onToggleDone: (task: Task) => void
  onToggleStar: (task: Task) => void
  onEdit: (task: Task) => void
  onDelete: (id: number) => void
}

export function TaskListRow({
  task,
  onToggleDone,
  onToggleStar,
  onEdit,
  onDelete,
}: Props) {
  const toast = useToast()
  const done = task.status === 'done'
  const starred = task.status === 'in_progress'
  const hasUrl = Boolean(task.url?.trim())
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: String(task.id),
    data: { status: task.status },
    disabled: hasUrl,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.45 : 1,
  }

  async function onCopyUrl() {
    const ok = await copyToClipboard(task.url || '')
    if (ok) toast.ok('URL copiada')
    else toast.err('No se pudo copiar')
  }

  return (
    <li
      ref={setNodeRef}
      style={style}
      className={`task-list__row${done ? ' is-done' : ''}${starred ? ' is-starred' : ''}`}
    >
      {hasUrl ? (
        <button
          type="button"
          className="task-list__copy"
          title="Copiar URL"
          aria-label="Copiar URL"
          onClick={() => void onCopyUrl()}
        >
          Copiar
        </button>
      ) : (
        <button
          type="button"
          className="task-list__grip"
          title="Arrastrar"
          aria-label="Arrastrar"
          {...attributes}
          {...listeners}
        >
          ⋮⋮
        </button>
      )}
      <label className="task-list__check">
        <input
          type="checkbox"
          checked={done}
          onChange={() => onToggleDone(task)}
          aria-label={done ? 'Marcar pendiente' : 'Marcar hecha'}
        />
      </label>
      <button
        type="button"
        className={`task-list__star${starred ? ' is-on' : ''}`}
        title={starred ? 'Quitar en curso' : 'En curso'}
        aria-pressed={starred}
        onClick={() => onToggleStar(task)}
      >
        {starred ? '★' : '☆'}
      </button>
      <button
        type="button"
        className="task-list__title"
        onClick={() => onEdit(task)}
      >
        {task.title}
      </button>
      <span className="task-list__meta">
        <ProjectChip project={task.project} />
        {task.due_at ? (
          <span className="muted task-list__due">{formatWhen(task.due_at)}</span>
        ) : null}
      </span>
      <button
        type="button"
        className="ghost task-list__edit"
        title="Editar"
        onClick={() => onEdit(task)}
      >
        ✎
      </button>
      <button
        type="button"
        className="ghost task-list__del"
        title="Borrar"
        onClick={() => onDelete(task.id)}
      >
        ×
      </button>
    </li>
  )
}
