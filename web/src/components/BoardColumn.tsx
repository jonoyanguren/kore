import { useDroppable } from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import type { BoardColumnId, Task } from '../types'
import { TaskCard } from './TaskCard'

const LABELS: Record<BoardColumnId, string> = {
  open: 'TODO',
  in_progress: 'En curso',
  done: 'Hechas',
}

type Props = {
  id: BoardColumnId
  tasks: Task[]
  onToggleDone: (task: Task) => void
  onToggleStar: (task: Task) => void
  onEdit: (task: Task) => void
  onDelete: (id: number) => void
}

export function BoardColumn({
  id,
  tasks,
  onToggleDone,
  onToggleStar,
  onEdit,
  onDelete,
}: Props) {
  const { setNodeRef, isOver } = useDroppable({ id })

  return (
    <section
      ref={setNodeRef}
      className={`board-col${isOver ? ' board-col--over' : ''}`}
    >
      <header className="board-col__head">
        <h2>{LABELS[id]}</h2>
        <span>{tasks.length}</span>
      </header>
      <SortableContext
        items={tasks.map((t) => String(t.id))}
        strategy={verticalListSortingStrategy}
      >
        <div className="board-col__list">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onToggleDone={onToggleDone}
              onToggleStar={onToggleStar}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
          {tasks.length === 0 ? (
            <p className="board-col__empty">Suelta aquí</p>
          ) : null}
        </div>
      </SortableContext>
    </section>
  )
}
