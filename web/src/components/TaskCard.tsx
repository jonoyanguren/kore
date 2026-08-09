import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { formatWhen } from '../dates'
import { copyToClipboard, shortUrlLabel } from '../lib/clipboard'
import type { Task } from '../types'
import { ProjectChip } from './ProjectChip'
import { useToast } from './Toasts'

type Props = {
  task: Task
  onToggleDone: (task: Task) => void
  onToggleStar: (task: Task) => void
  onEdit?: (task: Task) => void
  onDelete?: (id: number) => void
}

function CopyIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  )
}

export function TaskCard({
  task,
  onToggleDone,
  onToggleStar,
  onEdit,
  onDelete,
}: Props) {
  const toast = useToast()
  const hasUrl = Boolean(task.url?.trim())
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: String(task.id), data: { status: task.status } })

  const done = task.status === 'done'
  const starred = task.status === 'in_progress'

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.55 : 1,
  }

  async function onCopyUrl() {
    const ok = await copyToClipboard(task.url || '')
    if (ok) toast.ok('URL copiada')
    else toast.err('No se pudo copiar')
  }

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={`task-card${done ? ' is-done' : ''}${starred ? ' is-starred' : ''}`}
      {...attributes}
      {...listeners}
    >
      <header className="task-card__head">
        <button
          type="button"
          className={`task-card__check${done ? ' is-on' : ''}`}
          title={done ? 'Marcar pendiente' : 'Marcar hecha'}
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation()
            onToggleDone(task)
          }}
        >
          {done ? '✓' : '○'}
        </button>
        <button
          type="button"
          className={`task-card__star${starred ? ' is-on' : ''}`}
          title={starred ? 'Quitar en curso' : 'En curso'}
          aria-pressed={starred}
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation()
            onToggleStar(task)
          }}
        >
          {starred ? '★' : '☆'}
        </button>
        <h3
          className={onEdit ? 'task-card__title--edit' : undefined}
          title={onEdit ? 'Editar' : undefined}
          onPointerDown={(e) => {
            if (onEdit) e.stopPropagation()
          }}
          onClick={(e) => {
            if (!onEdit) return
            e.stopPropagation()
            onEdit(task)
          }}
        >
          {task.title}
        </h3>
        {hasUrl ? (
          <button
            type="button"
            className="task-card__edit"
            title="Copiar URL"
            aria-label="Copiar URL"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation()
              void onCopyUrl()
            }}
          >
            <CopyIcon />
          </button>
        ) : null}
        {onEdit ? (
          <button
            type="button"
            className="task-card__edit"
            title="Editar"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation()
              onEdit(task)
            }}
          >
            ✎
          </button>
        ) : null}
        {onDelete ? (
          <button
            type="button"
            className="task-card__edit"
            title="Borrar"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation()
              onDelete(task.id)
            }}
          >
            ×
          </button>
        ) : null}
      </header>
      <div className="task-card__meta">
        <ProjectChip project={task.project} />
        {task.due_at ? <span>{formatWhen(task.due_at)}</span> : null}
      </div>
      {hasUrl && task.url ? (
        <a
          href={task.url}
          target="_blank"
          rel="noreferrer"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
          title={task.url}
        >
          {shortUrlLabel(task.url)}
        </a>
      ) : null}
      {task.notes ? <p className="task-card__notes">{task.notes}</p> : null}
    </article>
  )
}
