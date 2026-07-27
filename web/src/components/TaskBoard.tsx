import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'
import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import {
  apiCompleteTask,
  apiCreateTask,
  apiListTasks,
  apiPatchTask,
} from '../api'
import type { BoardColumnId, Task } from '../types'
import { BoardColumn } from './BoardColumn'
import { TaskCard } from './TaskCard'

const COLUMNS: BoardColumnId[] = ['in_progress', 'open', 'done']

function columnOf(status: string): BoardColumnId | null {
  if (status === 'in_progress' || status === 'open' || status === 'done') {
    return status
  }
  return null
}

type Props = {
  refreshToken?: number
}

export function TaskBoard({ refreshToken = 0 }: Props) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [activeId, setActiveId] = useState<string | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  )

  async function reload() {
    const rows = await apiListTasks()
    setTasks(rows.filter((t) => t.status !== 'cancelled'))
  }

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        await reload()
      } catch (e) {
        if (!cancelled) setError(String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [refreshToken])

  const grouped = useMemo(() => {
    const map: Record<BoardColumnId, Task[]> = {
      in_progress: [],
      open: [],
      done: [],
    }
    for (const t of tasks) {
      const col = columnOf(t.status)
      if (col) map[col].push(t)
    }
    return map
  }, [tasks])

  const activeTask = activeId
    ? (tasks.find((t) => String(t.id) === activeId) ?? null)
    : null

  async function onAdd(e: FormEvent) {
    e.preventDefault()
    const t = title.trim()
    if (!t) return
    setTitle('')
    try {
      const task = await apiCreateTask({ title: t, status: 'open' })
      setTasks((prev) => [...prev, task])
    } catch (err) {
      setError(String(err))
    }
  }

  async function onComplete(id: number) {
    const prev = tasks
    setTasks((rows) =>
      rows.map((row) => (row.id === id ? { ...row, status: 'done' } : row)),
    )
    try {
      const updated = await apiCompleteTask(id)
      setTasks((rows) => rows.map((row) => (row.id === id ? updated : row)))
    } catch (err) {
      setTasks(prev)
      setError(String(err))
    }
  }

  async function moveTask(id: number, status: BoardColumnId) {
    const prev = tasks
    setTasks((rows) =>
      rows.map((row) => (row.id === id ? { ...row, status } : row)),
    )
    try {
      const updated = await apiPatchTask(id, { status })
      setTasks((rows) => rows.map((row) => (row.id === id ? updated : row)))
    } catch (err) {
      setTasks(prev)
      setError(String(err))
    }
  }

  function findColumn(id: string): BoardColumnId | null {
    if (COLUMNS.includes(id as BoardColumnId)) return id as BoardColumnId
    const task = tasks.find((t) => String(t.id) === id)
    return task ? columnOf(task.status) : null
  }

  function onDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id))
  }

  function onDragEnd(event: DragEndEvent) {
    setActiveId(null)
    const { active, over } = event
    if (!over) return
    const taskId = Number(active.id)
    const from = findColumn(String(active.id))
    const to = findColumn(String(over.id))
    if (!from || !to || from === to) return
    void moveTask(taskId, to)
  }

  return (
    <section className="board-panel">
      <header className="board-panel__bar">
        <h2>Tareas</h2>
        <form className="console__add" onSubmit={onAdd}>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Nueva tarea…"
          />
          <button type="submit">Añadir</button>
        </form>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {loading ? <p className="muted">Cargando…</p> : null}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
      >
        <div className="board">
          {COLUMNS.map((col) => (
            <BoardColumn
              key={col}
              id={col}
              tasks={grouped[col]}
              onComplete={onComplete}
            />
          ))}
        </div>
        <DragOverlay>
          {activeTask ? (
            <TaskCard task={activeTask} onComplete={() => undefined} />
          ) : null}
        </DragOverlay>
      </DndContext>
    </section>
  )
}
