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
  SortableContext,
  arrayMove,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
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
  apiDeleteTask,
  apiListTasks,
  apiPatchTask,
  apiPurgeCompletedTasks,
} from '../api'
import type { BoardColumnId, Task } from '../types'
import { BoardColumn } from './BoardColumn'
import { TaskCard } from './TaskCard'
import { TaskEditor } from './TaskEditor'
import { TaskListRow } from './TaskListRow'
import { useToast } from './Toasts'

const COLUMNS: BoardColumnId[] = ['open', 'in_progress', 'done']
const VIEW_KEY = 'kore.tasks.view'

type ViewMode = 'list' | 'board'

function columnOf(status: string): BoardColumnId | null {
  if (status === 'in_progress' || status === 'open' || status === 'done') {
    return status
  }
  return null
}

function withPriorities(ordered: Task[], status: BoardColumnId): Task[] {
  const n = ordered.length
  return ordered.map((t, i) => ({
    ...t,
    status,
    priority: n - i,
  }))
}

function loadView(): ViewMode {
  try {
    const v = localStorage.getItem(VIEW_KEY)
    if (v === 'list' || v === 'board') return v
  } catch {
    /* ignore */
  }
  return 'list'
}

export type TaskBoardHandle = {
  focusNewTask: () => void
  filterProject: (project: string) => void
  clearFilters: () => void
  openTask: (task: Task) => void
}

type Props = {
  refreshToken?: number
  companionName?: string
}

export const TaskBoard = forwardRef<TaskBoardHandle, Props>(function TaskBoard(
  { refreshToken = 0, companionName = 'Jone' },
  ref,
) {
  const toast = useToast()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [activeId, setActiveId] = useState<string | null>(null)
  const [editing, setEditing] = useState<Task | null>(null)
  const [view, setView] = useState<ViewMode>(loadView)
  const addInputRef = useRef<HTMLInputElement>(null)

  useImperativeHandle(ref, () => ({
    focusNewTask: () => {
      addInputRef.current?.focus()
      addInputRef.current?.scrollIntoView({ block: 'nearest' })
    },
    filterProject: () => {
      /* filters removed — project shown as chips */
    },
    clearFilters: () => {
      /* no-op */
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

  function setViewMode(mode: ViewMode) {
    setView(mode)
    try {
      localStorage.setItem(VIEW_KEY, mode)
    } catch {
      /* ignore */
    }
  }

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
    for (const col of COLUMNS) {
      map[col].sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0))
    }
    return map
  }, [tasks])

  const listOrdered = useMemo(() => {
    const rank = (s: string) =>
      s === 'in_progress' ? 0 : s === 'open' ? 1 : s === 'done' ? 2 : 3
    return [...tasks].sort((a, b) => {
      const d = rank(a.status) - rank(b.status)
      if (d !== 0) return d
      return (b.priority ?? 0) - (a.priority ?? 0)
    })
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
      const task = await apiCreateTask({
        title: t,
        status: 'open',
      })
      setTasks((prev) => [...prev, task])
      toast.ok('Tarea añadida')
    } catch (err) {
      const msg = String(err)
      setError(msg)
      toast.err(msg)
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
      toast.ok('Hecha')
    } catch (err) {
      setTasks(prev)
      const msg = String(err)
      setError(msg)
      toast.err(msg)
    }
  }

  async function onToggleDone(task: Task) {
    if (task.status === 'done') {
      await moveTask(task.id, 'open')
      return
    }
    await onComplete(task.id)
  }

  async function onToggleStar(task: Task) {
    if (task.status === 'in_progress') {
      await moveTask(task.id, 'open')
      return
    }
    await moveTask(task.id, 'in_progress')
  }

  async function onDelete(id: number) {
    const task = tasks.find((t) => t.id === id)
    if (!window.confirm(`¿Borrar «${task?.title ?? id}»?`)) return
    const prev = tasks
    setTasks((rows) => rows.filter((row) => row.id !== id))
    try {
      await apiDeleteTask(id)
      toast.ok('Borrada')
      if (editing?.id === id) setEditing(null)
    } catch (err) {
      setTasks(prev)
      const msg = String(err)
      setError(msg)
      toast.err(msg)
    }
  }

  async function onPurgeCompleted() {
    const n = tasks.filter((t) => t.status === 'done').length
    if (n === 0) {
      toast.ok('No hay completadas')
      return
    }
    if (
      !window.confirm(
        `¿Archivar y quitar ${n} completada${n === 1 ? '' : 's'} de la UI?\n` +
          `Quedan en vault/tasks/done.md para contexto de Jone; se borran de la BD.`,
      )
    ) {
      return
    }
    const prev = tasks
    setTasks((rows) => rows.filter((row) => row.status !== 'done'))
    if (editing?.status === 'done') setEditing(null)
    try {
      const deleted = await apiPurgeCompletedTasks()
      toast.ok(
        deleted === 0
          ? 'Nada que borrar'
          : `Archivadas ${deleted} · fuera de la UI`,
      )
    } catch (err) {
      setTasks(prev)
      const msg = String(err)
      setError(msg)
      toast.err(msg)
    }
  }

  /** Persist status/priority for a set of tasks; merge into local state. */
  async function persistTasks(
    nextSlice: Task[],
    toastMsg = 'Guardado',
  ): Promise<void> {
    const prev = tasks
    const byId = new Map(nextSlice.map((t) => [t.id, t]))
    setTasks((rows) => rows.map((row) => byId.get(row.id) ?? row))
    try {
      await Promise.all(
        nextSlice.map(async (t) => {
          const before = prev.find((x) => x.id === t.id)
          if (
            before &&
            before.status === t.status &&
            before.priority === t.priority
          ) {
            return
          }
          const updated = await apiPatchTask(t.id, {
            status: t.status,
            priority: t.priority,
          })
          setTasks((rows) =>
            rows.map((row) => (row.id === updated.id ? updated : row)),
          )
        }),
      )
      toast.ok(toastMsg)
    } catch (err) {
      setTasks(prev)
      const msg = String(err)
      setError(msg)
      toast.err(msg)
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
      toast.ok(
        status === 'open'
          ? 'Pendiente'
          : status === 'in_progress'
            ? 'En curso'
            : 'Movida',
      )
    } catch (err) {
      setTasks(prev)
      const msg = String(err)
      setError(msg)
      toast.err(msg)
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

  function onBoardDragEnd(event: DragEndEvent) {
    setActiveId(null)
    const { active, over } = event
    if (!over) return
    const activeTaskId = Number(active.id)
    const from = findColumn(String(active.id))
    const to = findColumn(String(over.id))
    if (!from || !to) return

    const fromList = [...grouped[from]]
    const oldIndex = fromList.findIndex((t) => t.id === activeTaskId)
    if (oldIndex < 0) return

    if (from === to) {
      const overIsColumn = COLUMNS.includes(over.id as BoardColumnId)
      const newIndex = overIsColumn
        ? fromList.length - 1
        : fromList.findIndex((t) => String(t.id) === String(over.id))
      if (newIndex < 0 || oldIndex === newIndex) return
      const reordered = withPriorities(
        arrayMove(fromList, oldIndex, newIndex),
        to,
      )
      void persistTasks(reordered, 'Orden guardado')
      return
    }

    const toList = [...grouped[to]]
    const [moved] = fromList.splice(oldIndex, 1)
    const overIsColumn = COLUMNS.includes(over.id as BoardColumnId)
    let newIndex = overIsColumn
      ? toList.length
      : toList.findIndex((t) => String(t.id) === String(over.id))
    if (newIndex < 0) newIndex = toList.length
    toList.splice(newIndex, 0, { ...moved, status: to })

    const nextFrom = withPriorities(fromList, from)
    const nextTo = withPriorities(toList, to)
    void persistTasks([...nextFrom, ...nextTo], 'Movida')
  }

  function onListDragEnd(event: DragEndEvent) {
    setActiveId(null)
    const { active, over } = event
    if (!over) return
    const oldIndex = listOrdered.findIndex(
      (t) => String(t.id) === String(active.id),
    )
    const newIndex = listOrdered.findIndex(
      (t) => String(t.id) === String(over.id),
    )
    if (oldIndex < 0 || newIndex < 0 || oldIndex === newIndex) return

    const overTask = listOrdered[newIndex]
    const nextStatus = columnOf(overTask.status)
    if (!nextStatus) return

    const moved = arrayMove(listOrdered, oldIndex, newIndex)
    const withStatus = moved.map((t) =>
      String(t.id) === String(active.id) ? { ...t, status: nextStatus } : t,
    )

    // Re-rank priorities inside each status bucket (order = list order).
    const buckets: Record<BoardColumnId, Task[]> = {
      in_progress: [],
      open: [],
      done: [],
    }
    for (const t of withStatus) {
      const col = columnOf(t.status)
      if (col) buckets[col].push(t)
    }
    const patched = COLUMNS.flatMap((col) => withPriorities(buckets[col], col))
    const changed = patched.filter((t) => {
      const before = tasks.find((x) => x.id === t.id)
      return (
        !before ||
        before.status !== t.status ||
        before.priority !== t.priority
      )
    })
    void persistTasks(
      changed,
      nextStatus !== columnOf(listOrdered[oldIndex].status)
        ? 'Movida'
        : 'Orden guardado',
    )
  }

  const doneCount = useMemo(
    () => tasks.filter((t) => t.status === 'done').length,
    [tasks],
  )

  return (
    <section className="board-panel">
      <header className="board-panel__bar">
        <h1 className="board-panel__title">Tareas</h1>
        <div className="view-toggle" role="group" aria-label="Vista">
          <button
            type="button"
            className={view === 'list' ? 'is-active' : ''}
            onClick={() => setViewMode('list')}
          >
            Lista
          </button>
          <button
            type="button"
            className={view === 'board' ? 'is-active' : ''}
            onClick={() => setViewMode('board')}
          >
            Columnas
          </button>
        </div>
        <button
          type="button"
          className="ghost board-panel__purge"
          disabled={doneCount === 0}
          title={
            doneCount === 0
              ? 'No hay completadas'
              : `Archivar ${doneCount} completada${doneCount === 1 ? '' : 's'} (vault + fuera UI)`
          }
          onClick={() => void onPurgeCompleted()}
        >
          Archivar
          {doneCount > 0 ? ` (${doneCount})` : ''}
        </button>
      </header>
      <form className="console__add board-panel__add" onSubmit={onAdd}>
        <input
          ref={addInputRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Nueva tarea…"
          aria-label="Nueva tarea"
        />
        <button type="submit">Añadir</button>
      </form>

      {error ? <p className="error">{error}</p> : null}
      {loading ? <p className="muted">Cargando…</p> : null}

      {view === 'list' ? (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={onDragStart}
          onDragEnd={onListDragEnd}
        >
          <SortableContext
            items={listOrdered.map((t) => String(t.id))}
            strategy={verticalListSortingStrategy}
          >
            <ul className="task-list">
              {listOrdered.map((task) => (
                <TaskListRow
                  key={task.id}
                  task={task}
                  onToggleDone={(t) => void onToggleDone(t)}
                  onToggleStar={(t) => void onToggleStar(t)}
                  onEdit={setEditing}
                  onDelete={(id) => void onDelete(id)}
                />
              ))}
              {!loading && listOrdered.length === 0 ? (
                <li className="task-list__empty muted empty-state">
                  <span className="empty-state__title">Sin tareas aquí</span>
                  <span>
                    Añade una arriba o pide a {companionName} en el chat.
                  </span>
                </li>
              ) : null}
            </ul>
          </SortableContext>
          <DragOverlay>
            {activeTask ? (
              <div className="task-list__row task-list__row--overlay">
                {activeTask.title}
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={onDragStart}
          onDragEnd={onBoardDragEnd}
        >
          <div className="board">
            {COLUMNS.map((col) => (
              <BoardColumn
                key={col}
                id={col}
                tasks={grouped[col]}
                onToggleDone={(t) => void onToggleDone(t)}
                onToggleStar={(t) => void onToggleStar(t)}
                onEdit={setEditing}
                onDelete={(id) => void onDelete(id)}
              />
            ))}
          </div>
          <DragOverlay>
            {activeTask ? (
              <TaskCard
                task={activeTask}
                onToggleDone={() => undefined}
                onToggleStar={() => undefined}
              />
            ) : null}
          </DragOverlay>
        </DndContext>
      )}

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
          onDeleted={(id) => {
            setTasks((rows) => rows.filter((row) => row.id !== id))
          }}
        />
      ) : null}
    </section>
  )
})
