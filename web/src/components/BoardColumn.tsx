import { useDroppable } from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import type { BoardColumnId, Task } from '../types'
import { TaskCard } from './TaskCard'

const LABELS: Record<BoardColumnId, string> = {
  in_progress: 'En curso',
  open: 'Pendientes',
  done: 'Hechas',
}

type Props = {
  id: BoardColumnId
  tasks: Task[]
  onComplete: (id: number) => void
}

export function BoardColumn({ id, tasks, onComplete }: Props) {
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
            <TaskCard key={task.id} task={task} onComplete={onComplete} />
          ))}
          {tasks.length === 0 ? (
            <p className="board-col__empty">Suelta aquí</p>
          ) : null}
        </div>
      </SortableContext>
    </section>
  )
}
