import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import type { Task } from '../types'

type Props = {
  task: Task
  onComplete: (id: number) => void
  onEdit?: (task: Task) => void
}

export function TaskCard({ task, onComplete, onEdit }: Props) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: String(task.id), data: { status: task.status } })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.55 : 1,
  }

  return (
    <article
      ref={setNodeRef}
      style={style}
      className="task-card"
      {...attributes}
      {...listeners}
    >
      <header className="task-card__head">
        <button
          type="button"
          className="task-card__check"
          title="Marcar hecha"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation()
            onComplete(task.id)
          }}
        >
          ✓
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
      </header>
      <div className="task-card__meta">
        {task.project ? <span>{task.project}</span> : null}
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
