import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  apiCreateDiary,
  apiCreateMemory,
  apiDeleteDiary,
  apiDeleteMemory,
  apiDeleteMemoryCategory,
  apiListDiary,
  apiListMemory,
  apiMemoryCategories,
  apiPrivacyOverview,
  apiVaultExport,
  type DiaryEntry,
  type MemoryItem,
  type PrivacyOverview,
} from '../api'
import { useToast } from './Toasts'

type Tab = 'diary' | 'memory' | 'privacy'

type Props = {
  open: boolean
  onClose: () => void
  initialTab?: Tab
}

export function MemoryDrawer({ open, onClose, initialTab = 'diary' }: Props) {
  const toast = useToast()
  const [tab, setTab] = useState<Tab>(initialTab)
  const [categories, setCategories] = useState<string[]>([])
  const [category, setCategory] = useState('')
  const [items, setItems] = useState<MemoryItem[]>([])
  const [diaryDay, setDiaryDay] = useState('')
  const [entries, setEntries] = useState<DiaryEntry[]>([])
  const [text, setText] = useState('')
  const [memCategory, setMemCategory] = useState('general')
  const [busy, setBusy] = useState(false)
  const [overview, setOverview] = useState<PrivacyOverview | null>(null)

  useEffect(() => {
    if (!open) return
    setTab(initialTab)
    setText('')
  }, [open, initialTab])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    ;(async () => {
      try {
        if (tab === 'diary') {
          const d = await apiListDiary()
          if (cancelled) return
          setDiaryDay(d.day)
          setEntries(d.entries)
        } else if (tab === 'memory') {
          const cats = await apiMemoryCategories()
          if (cancelled) return
          setCategories(cats)
          const rows = await apiListMemory(category || undefined)
          if (cancelled) return
          setItems(rows)
        } else {
          const ov = await apiPrivacyOverview()
          if (cancelled) return
          setOverview(ov)
        }
      } catch (e) {
        if (!cancelled) toast.err(String(e))
      }
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload on open/tab/category only
  }, [open, tab, category])

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  async function onAdd(e: FormEvent) {
    e.preventDefault()
    const t = text.trim()
    if (!t || busy) return
    setBusy(true)
    try {
      if (tab === 'diary') {
        const entry = await apiCreateDiary({ text: t })
        setEntries((prev) => [...prev, { id: entry.id, text: entry.text }])
        toast.ok('En diario')
      } else if (tab === 'memory') {
        const item = await apiCreateMemory({
          text: t,
          category: memCategory.trim() || 'general',
        })
        setItems((prev) => [item, ...prev])
        if (!categories.includes(item.category)) {
          setCategories((prev) => [...prev, item.category].sort())
        }
        toast.ok('En memoria')
      }
      setText('')
    } catch (err) {
      toast.err(String(err))
    } finally {
      setBusy(false)
    }
  }

  async function removeDiary(id: number) {
    try {
      await apiDeleteDiary(id)
      setEntries((prev) => prev.filter((x) => x.id !== id))
      toast.ok('Borrada')
    } catch (err) {
      toast.err(String(err))
    }
  }

  async function removeMemory(id: number) {
    try {
      await apiDeleteMemory(id)
      setItems((prev) => prev.filter((x) => x.id !== id))
      toast.ok('Borrada')
    } catch (err) {
      toast.err(String(err))
    }
  }

  async function wipeCategory(cat: string) {
    if (
      !window.confirm(
        `¿Borrar toda la categoría «${cat}» (${overview?.memory_categories.find((c) => c.category === cat)?.count ?? '?'} ítems)? No se puede deshacer.`,
      )
    ) {
      return
    }
    try {
      const n = await apiDeleteMemoryCategory(cat)
      toast.ok(`Borrados ${n} de «${cat}»`)
      const ov = await apiPrivacyOverview()
      setOverview(ov)
    } catch (err) {
      toast.err(String(err))
    }
  }

  async function onExport() {
    try {
      await apiVaultExport()
      toast.ok('Vault descargado')
    } catch (err) {
      toast.err(String(err))
    }
  }

  return (
    <div className="drawer" role="dialog" aria-modal="true" aria-label="Memoria">
      <button
        type="button"
        className="drawer__backdrop"
        aria-label="Cerrar"
        onClick={onClose}
      />
      <aside className="drawer__panel">
        <header className="drawer__head">
          <h2>Memoria</h2>
          <button type="button" className="ghost" onClick={onClose}>
            Cerrar
          </button>
        </header>

        <div className="drawer__tabs">
          <button
            type="button"
            className={tab === 'diary' ? 'is-active' : ''}
            onClick={() => setTab('diary')}
          >
            Diario
          </button>
          <button
            type="button"
            className={tab === 'memory' ? 'is-active' : ''}
            onClick={() => setTab('memory')}
          >
            Categorías
          </button>
          <button
            type="button"
            className={tab === 'privacy' ? 'is-active' : ''}
            onClick={() => setTab('privacy')}
          >
            Privacidad
          </button>
        </div>

        {tab === 'privacy' ? (
          <div className="drawer__privacy">
            <p className="muted">
              Qué sabe Kore de ti (SQLite + vault markdown). Exporta o borra por
              categoría.
            </p>
            {overview ? (
              <>
                <ul className="drawer__privacy-stats">
                  <li>
                    <strong>{overview.memory_total}</strong> hechos en memoria
                  </li>
                  <li>
                    <strong>{overview.diary_today}</strong> en diario hoy
                  </li>
                  <li>
                    <strong>{overview.tasks_open}</strong> tareas abiertas
                  </li>
                </ul>
                <button type="button" onClick={() => void onExport()}>
                  Descargar vault (.zip)
                </button>
                <h3 className="drawer__privacy-h">Categorías</h3>
                {overview.memory_categories.length === 0 ? (
                  <p className="muted">Sin memoria guardada</p>
                ) : (
                  <ul className="drawer__privacy-cats">
                    {overview.memory_categories.map((c) => (
                      <li key={c.category}>
                        <span>
                          <span className="drawer__cat">{c.category}</span>
                          <span className="muted"> · {c.count}</span>
                        </span>
                        <button
                          type="button"
                          className="ghost drawer__del"
                          onClick={() => void wipeCategory(c.category)}
                        >
                          Borrar
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            ) : (
              <p className="muted">Cargando…</p>
            )}
          </div>
        ) : (
          <>
            {tab === 'memory' ? (
              <div className="drawer__filters">
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  aria-label="Categoría"
                >
                  <option value="">Todas</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <p className="drawer__day muted">{diaryDay || 'hoy'}</p>
            )}

            <div className="drawer__list">
              {tab === 'diary' ? (
                entries.length === 0 ? (
                  <div className="empty-state">
                    <p className="empty-state__title">Diario vacío hoy</p>
                    <p className="muted">Añade una línea abajo o habla con Jone.</p>
                  </div>
                ) : (
                  <ul>
                    {entries.map((en) => (
                      <li key={en.id}>
                        <span>{en.text}</span>
                        <button
                          type="button"
                          className="ghost drawer__del"
                          onClick={() => void removeDiary(en.id)}
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                )
              ) : items.length === 0 ? (
                <div className="empty-state">
                  <p className="empty-state__title">Sin memoria aún</p>
                  <p className="muted">
                    Hechos durables por categoría (trabajo, gente, proyectos…).
                  </p>
                </div>
              ) : (
                <ul>
                  {items.map((it) => (
                    <li key={it.id}>
                      <div>
                        <span className="drawer__cat">{it.category}</span>
                        <span>{it.text}</span>
                      </div>
                      <button
                        type="button"
                        className="ghost drawer__del"
                        onClick={() => void removeMemory(it.id)}
                      >
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <form className="drawer__form" onSubmit={(e) => void onAdd(e)}>
              {tab === 'memory' ? (
                <input
                  value={memCategory}
                  onChange={(e) => setMemCategory(e.target.value)}
                  placeholder="categoría"
                  aria-label="Categoría nueva"
                />
              ) : null}
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={
                  tab === 'diary' ? 'Meter en el diario…' : 'Hecho durable…'
                }
                rows={3}
              />
              <button type="submit" disabled={busy || !text.trim()}>
                {tab === 'diary' ? 'Añadir al diario' : 'Guardar memoria'}
              </button>
            </form>
          </>
        )}
      </aside>
    </div>
  )
}
