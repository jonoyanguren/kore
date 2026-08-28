import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { apiDeleteTask, apiPatchTask } from '../api'
import type { Task, TaskStatus } from '../types'
import { useToast } from './Toasts'

type Props = {
  task: Task
  onClose: () => void
  onSaved: (task: Task) => void
  onDeleted?: (id: number) => void
}

const STATUSES: TaskStatus[] = ['open', 'in_progress', 'done', 'cancelled']

const STATUS_LABEL: Record<TaskStatus, string> = {
  open: 'Pendiente',
  in_progress: 'En curso',
  done: 'Hecha',
  cancelled: 'Cancelada',
}

export function TaskEditor({ task, onClose, onSaved, onDeleted }: Props) {
  const toast = useToast()
  const [title, setTitle] = useState(task.title)
  const [status, setStatus] = useState(task.status)
  const [project, setProject] = useState(task.project ?? '')
  const [url, setUrl] = useState(task.url ?? '')
  const [dueAt, setDueAt] = useState(task.due_at ?? '')
  const [notes, setNotes] = useState(task.notes ?? '')
  const [priority, setPriority] = useState(String(task.priority ?? 0))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setTitle(task.title)
    setStatus(task.status)
    setProject(task.project ?? '')
    setUrl(task.url ?? '')
    setDueAt(task.due_at ?? '')
    setNotes(task.notes ?? '')
    setPriority(String(task.priority ?? 0))
    setError(null)
  }, [task])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const t = title.trim()
    if (!t) {
      setError('Título vacío')
      toast.err('Título vacío')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const updated = await apiPatchTask(task.id, {
        title: t,
        status,
        priority: Number(priority) || 0,
        project: project.trim() || undefined,
        url: url.trim() || undefined,
        due_at: dueAt.trim() || undefined,
        notes: notes.trim() || undefined,
        clear_project: !project.trim(),
        clear_url: !url.trim(),
        clear_due: !dueAt.trim(),
        clear_notes: !notes.trim(),
      })
      toast.ok('Tarea guardada')
      onSaved(updated)
      onClose()
    } catch (err) {
      const msg = String(err)
      setError(msg)
      toast.err(msg)
    } finally {
      setBusy(false)
    }
  }

  async function onDelete() {
    if (!window.confirm(`¿Borrar «${task.title}»?`)) return
    setBusy(true)
    try {
      await apiDeleteTask(task.id)
      toast.ok('Borrada')
      onDeleted?.(task.id)
      onClose()
    } catch (err) {
      const msg = String(err)
      setError(msg)
      toast.err(msg)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="task-editor-backdrop"
      role="presentation"
      onClick={onClose}
    >
      <form
        className="task-editor"
        role="dialog"
        aria-label={`Editar tarea ${task.id}`}
        onClick={(e) => e.stopPropagation()}
        onSubmit={onSubmit}
      >
        <header className="task-editor__head">
          <div>
            <p className="task-editor__kicker">Tarea</p>
            <h3>{title.trim() || 'Sin título'}</h3>
          </div>
          <button type="button" className="ghost" onClick={onClose}>
            Cerrar
          </button>
        </header>

        <label>
          Título
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>

        <div className="task-editor__row">
          <label>
            Estado
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as TaskStatus)}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              ))}
            </select>
          </label>
          <label>
            Prioridad
            <input
              type="number"
              min={0}
              max={10}
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            />
          </label>
        </div>

        <div className="task-editor__row">
          <label>
            Proyecto
            <input
              value={project}
              onChange={(e) => setProject(e.target.value)}
              placeholder="kore, kimay, personal…"
            />
          </label>
          <label>
            Fecha
            <input
              type="date"
              value={dueAt}
              onChange={(e) => setDueAt(e.target.value)}
            />
          </label>
        </div>

        <label>
          URL
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://…"
          />
        </label>

        <label>
          Notas
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
          />
        </label>

        {error ? <p className="error">{error}</p> : null}

        <div className="task-editor__actions">
          <button
            type="button"
            className="ghost task-editor__danger"
            disabled={busy}
            onClick={() => void onDelete()}
          >
            Borrar
          </button>
          <button type="submit" disabled={busy}>
            Guardar
          </button>
        </div>
      </form>
    </div>
  )
}
