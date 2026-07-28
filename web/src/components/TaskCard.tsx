import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import type { Task } from '../types'
import { ProjectChip } from './ProjectChip'

type Props = {
  task: Task
  onToggleDone: (task: Task) => void
  onToggleStar: (task: Task) => void
  onEdit?: (task: Task) => void
  onDelete?: (id: number) => void
}

export function TaskCard({
  task,
  onToggleDone,
  onToggleStar,
  onEdit,
  onDelete,
}: Props) {
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
        {task.due_at ? <span>{task.due_at}</span> : null}
      </div>
      {task.url ? (
        <a
          href={task.url}
          target="_blank"
          rel="noreferrer"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          {task.url.replace(/^https?:\/\//, '').slice(0, 48)}
        </a>
      ) : null}
      {task.notes ? <p className="task-card__notes">{task.notes}</p> : null}
    </article>
  )
}
