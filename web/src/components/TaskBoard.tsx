import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react'
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
import { TaskEditor } from './TaskEditor'

const COLUMNS: BoardColumnId[] = ['open', 'in_progress', 'done']

function columnOf(status: string): BoardColumnId | null {
  if (status === 'in_progress' || status === 'open' || status === 'done') {
    return status
  }
  return null
}

export type TaskBoardHandle = {
  focusNewTask: () => void
  filterProject: (project: string) => void
  clearFilters: () => void
  openTask: (task: Task) => void
}

type Props = {
  refreshToken?: number
}

export const TaskBoard = forwardRef<TaskBoardHandle, Props>(function TaskBoard(
  { refreshToken = 0 },
  ref,
) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [activeId, setActiveId] = useState<string | null>(null)
  const [editing, setEditing] = useState<Task | null>(null)
  const [query, setQuery] = useState('')
  const [projectFilter, setProjectFilter] = useState('')
  const addInputRef = useRef<HTMLInputElement>(null)

  useImperativeHandle(ref, () => ({
    focusNewTask: () => {
      addInputRef.current?.focus()
      addInputRef.current?.scrollIntoView({ block: 'nearest' })
    },
    filterProject: (project: string) => setProjectFilter(project),
    clearFilters: () => {
      setQuery('')
      setProjectFilter('')
    },
    openTask: (task: Task) => setEditing(task),
  }))

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

  const projects = useMemo(() => {
    const set = new Set<string>()
    for (const t of tasks) {
      if (t.project) set.add(t.project)
    }
    return Array.from(set).sort()
  }, [tasks])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return tasks.filter((t) => {
      if (projectFilter && (t.project ?? '') !== projectFilter) return false
      if (!q) return true
      const hay = [t.title, t.project, t.notes, t.url, t.due_at]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      return hay.includes(q)
    })
  }, [tasks, query, projectFilter])

  const grouped = useMemo(() => {
    const map: Record<BoardColumnId, Task[]> = {
      in_progress: [],
      open: [],
      done: [],
    }
    for (const t of filtered) {
      const col = columnOf(t.status)
      if (col) map[col].push(t)
    }
    return map
  }, [filtered])

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
            ref={addInputRef}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Nueva tarea…"
          />
          <button type="submit">Añadir</button>
        </form>
      </header>

      <div className="board-panel__filters">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar…"
          aria-label="Buscar tareas"
        />
        <select
          value={projectFilter}
          onChange={(e) => setProjectFilter(e.target.value)}
          aria-label="Filtrar por proyecto"
        >
          <option value="">Todos los proyectos</option>
          {projects.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        {(query || projectFilter) && (
          <button
            type="button"
            className="ghost"
            onClick={() => {
              setQuery('')
              setProjectFilter('')
            }}
          >
            Limpiar
          </button>
        )}
      </div>

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
              onEdit={setEditing}
            />
          ))}
        </div>
        <DragOverlay>
          {activeTask ? (
            <TaskCard task={activeTask} onComplete={() => undefined} />
          ) : null}
        </DragOverlay>
      </DndContext>

      {editing ? (
        <TaskEditor
          task={editing}
          onClose={() => setEditing(null)}
          onSaved={(updated) => {
            setTasks((rows) =>
              rows
                .map((row) => (row.id === updated.id ? updated : row))
                .filter((row) => row.status !== 'cancelled'),
            )
          }}
        />
      ) : null}
    </section>
  )
})
