import { useEffect, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { apiListTasks } from '../api'
import type { DocsSectionId } from './DocsDrawer'

export type CommandAction =
  | { kind: 'chat'; text: string }
  | { kind: 'focus_new_task' }
  | { kind: 'filter_project'; project: string }
  | { kind: 'clear_filters' }
  | { kind: 'layout'; mode: 'day' | 'focus' | 'operate' }
  | { kind: 'open_memory'; tab?: 'diary' | 'memory' | 'privacy' }
  | { kind: 'open_docs'; section?: DocsSectionId }
  | { kind: 'logout' }

type Item = {
  id: string
  label: string
  hint?: string
  keywords: string
  action: CommandAction
}

type Props = {
  open: boolean
  onClose: () => void
  onRun: (action: CommandAction) => void
}

const STATIC: Item[] = [
  {
    id: 'layout-day',
    label: 'Vista Día',
    hint: '1',
    keywords: 'layout day día momentum briefing',
    action: { kind: 'layout', mode: 'day' },
  },
  {
    id: 'layout-focus',
    label: 'Vista Chat',
    hint: '2',
    keywords: 'layout focus chat',
    action: { kind: 'layout', mode: 'focus' },
  },
  {
    id: 'layout-operate',
    label: 'Vista Board',
    hint: '3',
    keywords: 'layout operate board tareas',
    action: { kind: 'layout', mode: 'operate' },
  },
  {
    id: 'memory-drawer',
    label: 'Memoria / diario',
    hint: 'drawer',
    keywords: 'memoria memory diario journal vault categorías',
    action: { kind: 'open_memory', tab: 'diary' },
  },
  {
    id: 'memory-cats',
    label: 'Categorías de memoria',
    hint: 'drawer',
    keywords: 'categorías memory hechos',
    action: { kind: 'open_memory', tab: 'memory' },
  },
  {
    id: 'privacy',
    label: 'Privacidad / export vault',
    hint: 'drawer',
    keywords: 'privacidad privacy export vault borrar',
    action: { kind: 'open_memory', tab: 'privacy' },
  },
  {
    id: 'docs',
    label: 'Cómo funciona Kore',
    hint: '?',
    keywords: 'docs documentación ayuda help jone guía',
    action: { kind: 'open_docs', section: 'que-es' },
  },
  {
    id: 'docs-skills',
    label: 'Docs: skills',
    hint: '?',
    keywords: 'docs skills playbooks dream capture tasks',
    action: { kind: 'open_docs', section: 'skills' },
  },
  {
    id: 'docs-comandos',
    label: 'Docs: comandos',
    hint: '?',
    keywords: 'docs comandos slash /tareas /dream /hora',
    action: { kind: 'open_docs', section: 'comandos' },
  },
  {
    id: 'docs-tareas',
    label: 'Docs: tareas',
    hint: '?',
    keywords: 'docs tareas check estrella board lista',
    action: { kind: 'open_docs', section: 'tareas' },
  },
  {
    id: 'dream',
    label: 'Sueño del día',
    hint: '/dream',
    keywords: 'dream sueño diario',
    action: { kind: 'chat', text: '/dream' },
  },
  {
    id: 'hora',
    label: 'Hora ahora',
    hint: '/hora',
    keywords: 'hora time clock',
    action: { kind: 'chat', text: '/hora' },
  },
  {
    id: 'agenda',
    label: 'Agenda de hoy',
    hint: '/agenda',
    keywords: 'agenda calendar calendario',
    action: { kind: 'chat', text: '/agenda' },
  },
  {
    id: 'diario-chat',
    label: 'Diario en chat',
    hint: '/diario',
    keywords: 'diario journal chat',
    action: { kind: 'chat', text: '/diario' },
  },
  {
    id: 'new',
    label: 'Nueva tarea',
    hint: 'foco en el board',
    keywords: 'nueva tarea add create',
    action: { kind: 'focus_new_task' },
  },
  {
    id: 'clear',
    label: 'Limpiar filtros del board',
    keywords: 'limpiar clear filtros filter',
    action: { kind: 'clear_filters' },
  },
  {
    id: 'logout',
    label: 'Salir',
    keywords: 'logout salir exit',
    action: { kind: 'logout' },
  },
]

export function CommandPalette({ open, onClose, onRun }: Props) {
  const [q, setQ] = useState('')
  const [projects, setProjects] = useState<string[]>([])
  const [active, setActive] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) return
    setQ('')
    setActive(0)
    void apiListTasks()
      .then((rows) => {
        const set = new Set<string>()
        for (const t of rows) {
          if (t.project && t.status !== 'cancelled') set.add(t.project)
        }
        setProjects(Array.from(set).sort())
      })
      .catch(() => setProjects([]))
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [open])

  const items = useMemo(() => {
    const projectItems: Item[] = projects.map((p) => ({
      id: `proj-${p}`,
      label: `Proyecto: ${p}`,
      hint: 'filtrar board',
      keywords: `proyecto project ${p}`,
      action: { kind: 'filter_project', project: p },
    }))
    const all = [...STATIC, ...projectItems]
    const needle = q.trim().toLowerCase()
    if (!needle) return all
    return all.filter(
      (it) =>
        it.label.toLowerCase().includes(needle) ||
        it.keywords.toLowerCase().includes(needle) ||
        (it.hint ?? '').toLowerCase().includes(needle),
    )
  }, [q, projects])

  useEffect(() => {
    setActive(0)
  }, [q])

  useEffect(() => {
    if (!open) return
    function onKey(e: globalThis.KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  function run(item: Item) {
    onRun(item.action)
    onClose()
  }

  function onInputKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((i) => Math.min(i + 1, Math.max(items.length - 1, 0)))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const item = items[active]
      if (item) run(item)
    }
  }

  return (
    <div className="cmdk" role="dialog" aria-modal="true" aria-label="Comandos">
      <button type="button" className="cmdk__backdrop" aria-label="Cerrar" onClick={onClose} />
      <div className="cmdk__panel">
        <input
          ref={inputRef}
          className="cmdk__input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={onInputKey}
          placeholder="Buscar comando…"
          aria-label="Buscar comando"
        />
        <ul className="cmdk__list" role="listbox">
          {items.length === 0 ? (
            <li className="cmdk__empty muted">Nada coincide</li>
          ) : (
            items.map((it, i) => (
              <li key={it.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={i === active}
                  className={`cmdk__item${i === active ? ' cmdk__item--active' : ''}`}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => run(it)}
                >
                  <span>{it.label}</span>
                  {it.hint ? <span className="cmdk__hint">{it.hint}</span> : null}
                </button>
              </li>
            ))
          )}
        </ul>
        <p className="cmdk__footer muted">↑↓ navegar · Enter · Esc</p>
      </div>
    </div>
  )
}
