import { useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  apiCancelMission,
  apiCreateMission,
  apiGetMission,
  apiListMissions,
} from '../api'
import type { Mission } from '../types'
import { useToast } from './Toasts'

type Props = {
  active?: boolean
}

const STATUS_LABEL: Record<string, string> = {
  draft: 'Borrador',
  clarifying: 'Aclarando',
  queued: 'En cola',
  running: 'Corriendo',
  waiting: 'Esperando',
  done: 'Hecha',
  failed: 'Falló',
  cancelled: 'Cancelada',
}

function isDoneStatus(s: string): boolean {
  return s === 'done' || s === 'failed' || s === 'cancelled'
}

/** Minimal markdown → HTML for mission results (no extra deps). */
function renderMarkdown(md: string): string {
  const esc = (s: string) =>
    s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
  const lines = md.replace(/\r\n/g, '\n').split('\n')
  const out: string[] = []
  let inList = false
  let inQuote = false

  function closeList() {
    if (inList) {
      out.push('</ul>')
      inList = false
    }
  }
  function closeQuote() {
    if (inQuote) {
      out.push('</blockquote>')
      inQuote = false
    }
  }

  function inline(s: string): string {
    return esc(s)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
  }

  for (const raw of lines) {
    const line = raw
    if (/^###\s+/.test(line)) {
      closeList()
      closeQuote()
      out.push(`<h3>${inline(line.replace(/^###\s+/, ''))}</h3>`)
      continue
    }
    if (/^##\s+/.test(line)) {
      closeList()
      closeQuote()
      out.push(`<h2>${inline(line.replace(/^##\s+/, ''))}</h2>`)
      continue
    }
    if (/^#\s+/.test(line)) {
      closeList()
      closeQuote()
      out.push(`<h1>${inline(line.replace(/^#\s+/, ''))}</h1>`)
      continue
    }
    if (/^>\s?/.test(line)) {
      closeList()
      if (!inQuote) {
        out.push('<blockquote>')
        inQuote = true
      }
      out.push(`<p>${inline(line.replace(/^>\s?/, ''))}</p>`)
      continue
    }
    if (/^[-*]\s+/.test(line)) {
      closeQuote()
      if (!inList) {
        out.push('<ul>')
        inList = true
      }
      out.push(`<li>${inline(line.replace(/^[-*]\s+/, ''))}</li>`)
      continue
    }
    if (!line.trim()) {
      closeList()
      closeQuote()
      continue
    }
    closeList()
    closeQuote()
    out.push(`<p>${inline(line)}</p>`)
  }
  closeList()
  closeQuote()
  return out.join('\n')
}

export function MissionsPanel({ active = true }: Props) {
  const [missions, setMissions] = useState<Mission[]>([])
  const [hideDone, setHideDone] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<Mission | null>(null)
  const [creating, setCreating] = useState(false)
  const [title, setTitle] = useState('')
  const [brief, setBrief] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const toast = useToast()

  async function loadList() {
    try {
      const rows = await apiListMissions(!hideDone)
      setMissions(rows)
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }

  useEffect(() => {
    if (!active) return
    void loadList()
    const id = window.setInterval(() => void loadList(), 4000)
    return () => window.clearInterval(id)
  }, [active, hideDone])

  useEffect(() => {
    if (!active || selectedId == null) {
      setDetail(null)
      return
    }
    let cancelled = false
    async function load() {
      try {
        const m = await apiGetMission(selectedId!)
        if (!cancelled) setDetail(m)
      } catch (e) {
        if (!cancelled) toast.err(String(e))
      }
    }
    void load()
    const id = window.setInterval(() => void load(), 4000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [active, selectedId])

  const visible = useMemo(() => {
    if (!hideDone) return missions
    return missions.filter((m) => !isDoneStatus(m.status))
  }, [missions, hideDone])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    if (!title.trim() || busy) return
    setBusy(true)
    try {
      const m = await apiCreateMission({
        title: title.trim(),
        brief: brief.trim(),
        launch: true,
        max_ticks: 3,
        tick_seconds: 20,
      })
      toast.ok(`Misión #${m.id} en cola`)
      setTitle('')
      setBrief('')
      setCreating(false)
      setSelectedId(m.id)
      await loadList()
    } catch (err) {
      toast.err(String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onCancel(id: number) {
    setBusy(true)
    try {
      await apiCancelMission(id)
      toast.ok('Cancelada')
      await loadList()
      if (selectedId === id) {
        const m = await apiGetMission(id)
        setDetail(m)
      }
    } catch (err) {
      toast.err(String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="missions">
      <header className="missions__bar">
        <h2 className="missions__title">Misiones</h2>
        <label className="missions__hide">
          <input
            type="checkbox"
            checked={hideDone}
            onChange={(e) => setHideDone(e.target.checked)}
          />
          Ocultar terminadas
        </label>
        <button
          type="button"
          className="missions__new"
          onClick={() => setCreating((v) => !v)}
        >
          {creating ? 'Cerrar' : 'Nueva'}
        </button>
      </header>

      {creating ? (
        <form className="missions__form" onSubmit={(e) => void onCreate(e)}>
          <label>
            Título
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Casas en Cantabria…"
              required
              maxLength={200}
              disabled={busy}
            />
          </label>
          <label>
            Encargo
            <textarea
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              placeholder="Condiciones, presupuesto, zona…"
              rows={4}
              disabled={busy}
            />
          </label>
          <p className="muted missions__form-hint">
            v1: formulario → se lanza al instante (loop stub). Aclaración con
            preguntas, luego.
          </p>
          <button type="submit" disabled={busy || !title.trim()}>
            {busy ? '…' : 'Lanzar'}
          </button>
        </form>
      ) : null}

      {error ? <p className="muted">{error}</p> : null}

      <div className="missions__body">
        <ul className="missions__list">
          {visible.length === 0 ? (
            <li className="missions__empty muted">
              Ninguna misión. Pulsa Nueva para crear una.
            </li>
          ) : (
            visible.map((m) => (
              <li key={m.id}>
                <button
                  type="button"
                  className={
                    selectedId === m.id
                      ? 'missions__item missions__item--active'
                      : 'missions__item'
                  }
                  onClick={() => setSelectedId(m.id)}
                >
                  <span className="missions__item-title">{m.title}</span>
                  <span className="missions__item-meta muted">
                    {STATUS_LABEL[m.status] ?? m.status}
                    {m.status === 'waiting' || m.status === 'running'
                      ? ` · ${m.step_index}/${m.max_ticks}`
                      : null}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>

        <div className="missions__detail">
          {!detail ? (
            <p className="muted">Elige una misión para ver el resultado.</p>
          ) : (
            <>
              <div className="missions__detail-bar">
                <div>
                  <h3>{detail.title}</h3>
                  <p className="muted">
                    {STATUS_LABEL[detail.status] ?? detail.status}
                    {detail.result_path
                      ? ` · ${detail.result_path}`
                      : null}
                  </p>
                </div>
                {!isDoneStatus(detail.status) ? (
                  <button
                    type="button"
                    className="ghost"
                    disabled={busy}
                    onClick={() => void onCancel(detail.id)}
                  >
                    Cancelar
                  </button>
                ) : null}
              </div>
              <article
                className="missions__md"
                dangerouslySetInnerHTML={{
                  __html: renderMarkdown(detail.markdown || '_Sin contenido aún._'),
                }}
              />
            </>
          )}
        </div>
      </div>
    </section>
  )
}
