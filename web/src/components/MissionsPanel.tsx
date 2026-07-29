import { useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  apiCancelMission,
  apiClarifyMission,
  apiCreateMission,
  apiGetMission,
  apiListMissions,
  apiRelaunchMission,
  type ClarifyHistoryItem,
} from '../api'
import { renderMissionMarkdown } from '../lib/missionMarkdown'
import type { Mission } from '../types'
import { useToast } from './Toasts'

type Props = {
  active?: boolean
}

type FormPhase = 'draft' | 'questions' | 'ready'

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

function isActiveStatus(s: string): boolean {
  return s === 'queued' || s === 'running' || s === 'waiting'
}

export function MissionsPanel({ active = true }: Props) {
  const [missions, setMissions] = useState<Mission[]>([])
  const [hideDone, setHideDone] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<Mission | null>(null)
  const [creating, setCreating] = useState(false)
  const [title, setTitle] = useState('')
  const [brief, setBrief] = useState('')
  const [phase, setPhase] = useState<FormPhase>('draft')
  const [questions, setQuestions] = useState<string[]>([])
  const [answers, setAnswers] = useState<string[]>([])
  const [history, setHistory] = useState<ClarifyHistoryItem[]>([])
  const [round, setRound] = useState(1)
  const [refinedBrief, setRefinedBrief] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const toast = useToast()

  const panelOpen = selectedId != null

  function resetForm() {
    setTitle('')
    setBrief('')
    setPhase('draft')
    setQuestions([])
    setAnswers([])
    setHistory([])
    setRound(1)
    setRefinedBrief('')
  }

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
    const id = window.setInterval(() => void load(), 3000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [active, selectedId])

  useEffect(() => {
    if (!panelOpen) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setSelectedId(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [panelOpen])

  const visible = useMemo(() => {
    if (!hideDone) return missions
    return missions.filter((m) => !isDoneStatus(m.status))
  }, [missions, hideDone])

  async function runClarify(
    nextHistory: ClarifyHistoryItem[],
    nextRound: number,
  ) {
    const result = await apiClarifyMission({
      title: title.trim(),
      brief: brief.trim(),
      history: nextHistory,
      round: nextRound,
    })
    setRound(result.round)
    setRefinedBrief(result.refined_brief)
    if (result.ready || result.questions.length === 0) {
      setPhase('ready')
      setQuestions([])
      setAnswers([])
      return
    }
    setPhase('questions')
    setQuestions(result.questions)
    setAnswers(result.questions.map(() => ''))
  }

  async function onContinue(e: FormEvent) {
    e.preventDefault()
    if (!title.trim() || busy) return
    setBusy(true)
    try {
      await runClarify([], 1)
    } catch (err) {
      toast.err(String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onAnswer(e: FormEvent) {
    e.preventDefault()
    if (busy || questions.length === 0) return
    setBusy(true)
    try {
      const turns: ClarifyHistoryItem[] = questions.map((q, i) => ({
        question: q,
        answer: (answers[i] || '').trim(),
      }))
      const nextHistory = [...history, ...turns]
      setHistory(nextHistory)
      await runClarify(nextHistory, Math.min(round + 1, 2))
    } catch (err) {
      toast.err(String(err))
    } finally {
      setBusy(false)
    }
  }

  async function launchWithBrief(finalBrief: string) {
    if (!title.trim() || busy) return
    setBusy(true)
    try {
      const m = await apiCreateMission({
        title: title.trim(),
        brief: finalBrief.trim(),
        launch: true,
        max_ticks: 3,
        tick_seconds: 10,
      })
      toast.ok(`Misión #${m.id} en cola`)
      resetForm()
      setCreating(false)
      setSelectedId(m.id)
      await loadList()
    } catch (err) {
      toast.err(String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onLaunch(e: FormEvent) {
    e.preventDefault()
    await launchWithBrief(refinedBrief || brief)
  }

  async function onSkipClarify() {
    await launchWithBrief(brief)
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

  async function onRelaunch(id: number) {
    setBusy(true)
    try {
      const m = await apiRelaunchMission(id)
      toast.ok(`Relanzada #${m.id}`)
      setSelectedId(m.id)
      await loadList()
      setDetail(await apiGetMission(id))
    } catch (err) {
      toast.err(String(err))
    } finally {
      setBusy(false)
    }
  }

  function closePanel() {
    setSelectedId(null)
  }

  const md = (detail?.markdown || '').trim()

  return (
    <section className={`missions${panelOpen ? ' missions--panel' : ''}`}>
      <div className="missions__main">
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
            onClick={() => {
              if (creating) resetForm()
              setCreating((v) => !v)
            }}
          >
            {creating ? 'Cerrar' : 'Nueva'}
          </button>
        </header>

        {creating ? (
          <div className="missions__form">
            {phase === 'draft' ? (
              <form onSubmit={(e) => void onContinue(e)}>
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
                  Primero aclaramos 1–2 puntos si hace falta; luego investiga en
                  web (3 ticks).
                </p>
                <div className="missions__form-actions">
                  <button type="submit" disabled={busy || !title.trim()}>
                    {busy ? '…' : 'Continuar'}
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    disabled={busy || !title.trim()}
                    onClick={() => void onSkipClarify()}
                  >
                    Lanzar sin aclarar
                  </button>
                </div>
              </form>
            ) : null}

            {phase === 'questions' ? (
              <form onSubmit={(e) => void onAnswer(e)}>
                <p className="missions__clarify-lede">
                  Antes de lanzar, unas preguntas:
                </p>
                {questions.map((q, i) => (
                  <label key={`${round}-${i}`}>
                    {q}
                    <textarea
                      value={answers[i] ?? ''}
                      onChange={(e) => {
                        const next = [...answers]
                        next[i] = e.target.value
                        setAnswers(next)
                      }}
                      rows={2}
                      disabled={busy}
                      required
                    />
                  </label>
                ))}
                <div className="missions__form-actions">
                  <button type="submit" disabled={busy}>
                    {busy ? '…' : 'Responder'}
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    disabled={busy}
                    onClick={() => void onSkipClarify()}
                  >
                    Lanzar igual
                  </button>
                </div>
              </form>
            ) : null}

            {phase === 'ready' ? (
              <form onSubmit={(e) => void onLaunch(e)}>
                <p className="missions__clarify-lede">
                  Brief listo. Puedes editarlo antes de lanzar.
                </p>
                <label>
                  Título
                  <input value={title} disabled readOnly />
                </label>
                <label>
                  Encargo final
                  <textarea
                    value={refinedBrief}
                    onChange={(e) => setRefinedBrief(e.target.value)}
                    rows={6}
                    disabled={busy}
                  />
                </label>
                <div className="missions__form-actions">
                  <button
                    type="submit"
                    disabled={busy || !refinedBrief.trim()}
                  >
                    {busy ? '…' : 'Lanzar'}
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    disabled={busy}
                    onClick={() => {
                      setPhase('draft')
                      setQuestions([])
                      setAnswers([])
                      setHistory([])
                      setRound(1)
                    }}
                  >
                    Volver
                  </button>
                </div>
              </form>
            ) : null}
          </div>
        ) : null}

        {error ? <p className="muted">{error}</p> : null}

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
                    {STATUS_LABEL[m.status] || m.status}
                    {isActiveStatus(m.status)
                      ? ` · ${m.step_index}/${m.max_ticks}`
                      : ''}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>

      {panelOpen ? (
        <aside className="missions__panel" aria-label="Resumen de misión">
          <div className="missions__panel-bar">
            <button
              type="button"
              className="ghost missions__panel-close"
              onClick={closePanel}
            >
              Cerrar
            </button>
            <div className="missions__panel-actions">
              {detail && !isDoneStatus(detail.status) ? (
                <button
                  type="button"
                  className="ghost"
                  disabled={busy}
                  onClick={() => void onCancel(detail.id)}
                >
                  Cancelar
                </button>
              ) : null}
              {detail && isDoneStatus(detail.status) ? (
                <button
                  type="button"
                  className="ghost"
                  disabled={busy}
                  onClick={() => void onRelaunch(detail.id)}
                >
                  Relanzar
                </button>
              ) : null}
            </div>
          </div>
          {!detail ? (
            <p className="muted missions__panel-loading">Cargando…</p>
          ) : (
            <>
              <header className="missions__panel-head">
                <h3>{detail.title}</h3>
                <p className="muted">
                  {STATUS_LABEL[detail.status] || detail.status}
                  {isActiveStatus(detail.status)
                    ? ` · tick ${detail.step_index}/${detail.max_ticks}`
                    : ''}
                </p>
              </header>
              {md ? (
                <div
                  className="missions__md"
                  dangerouslySetInnerHTML={{ __html: renderMissionMarkdown(md) }}
                />
              ) : (
                <p className="muted">Sin informe aún.</p>
              )}
            </>
          )}
        </aside>
      ) : null}
    </section>
  )
}
