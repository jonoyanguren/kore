import { useEffect, useMemo, useRef, useState, type ClipboardEvent, type FormEvent } from 'react'
import {
  apiAskMission,
  apiCancelMission,
  apiClarifyMission,
  apiCreateMission,
  apiGetMission,
  apiListMissions,
  apiMissionModeOptions,
  apiRelaunchMission,
  isLlmCapError,
  LLM_CAP_COPY,
  type ClarifyHistoryItem,
  type ClarifyQuestion,
} from '../api'
import { cleanCopiedText, copyToClipboard } from '../lib/clipboard'
import { renderMissionMarkdown } from '../lib/missionMarkdown'
import { bindMissionImages } from '../lib/bindMissionImages'
import {
  sectionToMarkdown,
  splitMissionMarkdown,
} from '../lib/missionReport'
import type { Mission, MissionCostInfo, MissionMode, MissionModeOption } from '../types'
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

function sameMissionView(a: Mission, b: Mission): boolean {
  return (
    a.status === b.status &&
    a.markdown === b.markdown &&
    a.step_index === b.step_index &&
    a.error === b.error &&
    (a.asks?.length ?? 0) === (b.asks?.length ?? 0) &&
    (a.plan?.completed ?? -1) === (b.plan?.completed ?? -1) &&
    (a.plan?.total ?? -1) === (b.plan?.total ?? -1) &&
    (a.plan?.cost?.usd ?? 0) === (b.plan?.cost?.usd ?? 0)
  )
}

function missionProgressLabel(m: Mission): string {
  const plan = m.plan
  if (!plan?.total) {
    if (isActiveStatus(m.status)) return 'planificando…'
    return ''
  }
  if (m.status === 'done') return `${plan.total} tareas`
  const current = Math.min(m.step_index + 1, plan.total)
  return `tarea ${current}/${plan.total}`
}

function taskStatusMark(status: string): string {
  if (status === 'done') return '✓'
  if (status === 'running') return '›'
  if (status === 'failed') return '✕'
  return '○'
}

function formatMissionCost(cost: MissionCostInfo): string {
  const usd = cost.usd
  if (usd <= 0) return '$0.00'
  let text: string
  if (usd < 0.01) text = `$${usd.toFixed(4)}`
  else if (usd < 1) text = `$${usd.toFixed(3)}`
  else text = `$${usd.toFixed(2)}`
  return cost.estimated ? `~${text}` : text
}

function composeAnswer(choice: string, extra: string): string {
  const c = choice.trim()
  const e = extra.trim()
  if (c && e) return `${c}. ${e}`
  return c || e
}

function missionListCost(m: Mission): string | null {
  const cost = m.plan?.cost
  if (!cost || cost.usd <= 0) return null
  return formatMissionCost(cost)
}

const FALLBACK_MODES: MissionModeOption[] = [
  {
    id: 'normal',
    label: 'Rápido',
    when: 'Salir del bloqueo con una recomendación',
    legend: 'Te dejo una decisión y un siguiente paso.',
    outcome: 'Salida: decisión · por qué · opciones · siguiente paso · fuentes',
    blurb: 'Para desatascar',
    model: '',
    approx_usd: 0.04,
    approx_label: '~$0.02–0.06',
  },
  {
    id: 'experto',
    label: 'A fondo',
    when: 'Cuando importa acertar',
    legend: 'Informe denso: opciones comparadas, evidencia y fuentes.',
    outcome: 'Salida: juicio · evidencia · contraste · siguiente paso · fuentes',
    blurb: 'Informe para decidir en serio',
    model: '',
    approx_usd: 0.2,
    approx_label: '~$0.10–0.30',
  },
]

function missionModeId(m: Mission): string {
  return m.mode || m.quality || 'normal'
}

function missionModeLabel(m: Mission, options: MissionModeOption[]): string {
  if (m.mode_label) return m.mode_label
  const id = missionModeId(m)
  const hit = options.find((o) => o.id === id)
  if (hit) return hit.label
  if (id === 'pro' || id === 'experto') return 'A fondo'
  if (id === 'normal') return 'Rápido'
  return id.charAt(0).toUpperCase() + id.slice(1)
}

function modeTone(id: string): MissionMode {
  if (id === 'pro' || id === 'experto') return 'experto'
  if (id === 'loco' || id === 'duro') return id
  return 'normal'
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
  const [questions, setQuestions] = useState<ClarifyQuestion[]>([])
  const [answers, setAnswers] = useState<string[]>([])
  const [picked, setPicked] = useState<string[]>([])
  const [history, setHistory] = useState<ClarifyHistoryItem[]>([])
  const [round, setRound] = useState(1)
  const [refinedBrief, setRefinedBrief] = useState('')
  const [mode, setMode] = useState<MissionMode>('normal')
  const [modeOptions, setModeOptions] =
    useState<MissionModeOption[]>(FALLBACK_MODES)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [askText, setAskText] = useState('')
  const [askBusy, setAskBusy] = useState(false)
  const toast = useToast()
  const capErr = (err: unknown) =>
    toast.err(isLlmCapError(err) ? LLM_CAP_COPY : String(err))
  const resultRef = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLElement>(null)

  const panelOpen = selectedId != null
  const selectedMode =
    modeOptions.find((o) => o.id === mode) || FALLBACK_MODES[0]

  function resetForm() {
    setTitle('')
    setBrief('')
    setPhase('draft')
    setQuestions([])
    setAnswers([])
    setPicked([])
    setHistory([])
    setRound(1)
    setRefinedBrief('')
    setMode('normal')
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
    let cancelled = false
    void apiMissionModeOptions()
      .then((opts) => {
        if (!cancelled && opts.length) setModeOptions(opts)
      })
      .catch(() => {
        /* fallback UI labels below */
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!active || selectedId == null) {
      setDetail(null)
      setAskText('')
      return
    }
    let cancelled = false
    let intervalId: number | undefined
    async function load() {
      try {
        const m = await apiGetMission(selectedId!)
        if (cancelled) return
        setDetail((prev) => (prev && sameMissionView(prev, m) ? prev : m))
        if (isDoneStatus(m.status) && intervalId != null) {
          window.clearInterval(intervalId)
          intervalId = undefined
        }
      } catch (e) {
        if (!cancelled) toast.err(String(e))
      }
    }
    void load()
    intervalId = window.setInterval(() => void load(), 3000)
    return () => {
      cancelled = true
      if (intervalId != null) window.clearInterval(intervalId)
    }
  }, [active, selectedId])

  useEffect(() => {
    const el = panelRef.current
    if (!el || !panelOpen) return
    return bindMissionImages(el)
  }, [panelOpen])

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
      mode,
    })
    setRound(result.round)
    setRefinedBrief(result.refined_brief)
    if (result.ready || result.questions.length === 0) {
      setPhase('ready')
      setQuestions([])
      setAnswers([])
      setPicked([])
      return
    }
    setPhase('questions')
    setQuestions(result.questions)
    setAnswers(result.questions.map(() => ''))
    setPicked(result.questions.map(() => ''))
  }

  async function onContinue(e: FormEvent) {
    e.preventDefault()
    if (!title.trim() || busy) return
    setBusy(true)
    try {
      await runClarify([], 1)
    } catch (err) {
      capErr(err)
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
        question: q.prompt,
        answer: composeAnswer(picked[i] || '', answers[i] || ''),
      }))
      const nextHistory = [...history, ...turns]
      setHistory(nextHistory)
      await runClarify(nextHistory, round + 1)
    } catch (err) {
      capErr(err)
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
        tick_seconds: 10,
        mode,
      })
      toast.ok(`Misión #${m.id} en cola`)
      resetForm()
      setCreating(false)
      setSelectedId(m.id)
      await loadList()
    } catch (err) {
      capErr(err)
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

  function modeField(variant: 'cards' | 'pills' = 'cards') {
    const approx = selectedMode.approx_label
    return (
      <div className="missions__mode">
        <span className="missions__mode-label" id="missions-mode-label">
          Qué te entrego
        </span>
        <div
          className={
            variant === 'pills' ? 'missions__mode-pills' : 'missions__mode-grid'
          }
          role="radiogroup"
          aria-labelledby="missions-mode-label"
        >
          {modeOptions.map((o) => {
            const active = o.id === mode
            const tone = modeTone(String(o.id))
            return (
              <button
                key={o.id}
                type="button"
                role="radio"
                aria-checked={active}
                disabled={busy}
                className={
                  (variant === 'pills'
                    ? 'missions__mode-pill'
                    : 'missions__mode-card') +
                  ` missions__mode--${tone}` +
                  (active ? ' is-active' : '')
                }
                onClick={() => setMode(o.id as MissionMode)}
              >
                <span className="missions__mode-name">{o.label}</span>
                {variant === 'cards' ? (
                  <span className="missions__mode-copy">{o.legend}</span>
                ) : null}
              </button>
            )
          })}
        </div>
        <p className="muted missions__mode-hint">
          {selectedMode.outcome || selectedMode.when}
          {' · '}
          {approx} / misión
        </p>
      </div>
    )
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
      capErr(err)
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
      capErr(err)
    } finally {
      setBusy(false)
    }
  }

  function closePanel() {
    setSelectedId(null)
  }

  const md = (detail?.markdown || '').trim()
  const report = useMemo(() => splitMissionMarkdown(md), [md])
  const missionRunning = detail ? isActiveStatus(detail.status) : false
  const showLiveResearch =
    missionRunning && !report.result && report.research.length > 0
  const showFullResearch =
    Boolean(report.result) && report.detailMarkdown.trim().length > 0

  function onCopyResult(e: ClipboardEvent<HTMLDivElement>) {
    const cleaned = cleanCopiedText(window.getSelection()?.toString() ?? '')
    if (!cleaned || !e.clipboardData) return
    e.preventDefault()
    e.clipboardData.setData('text/plain', cleaned)
  }

  async function copyResult() {
    const fromDom = resultRef.current?.innerText || ''
    const fallback = report.result?.body || ''
    const ok = await copyToClipboard(fromDom || fallback)
    if (ok) toast.ok('Copiado')
    else toast.err('No se pudo copiar')
  }

  async function onAsk(e: FormEvent) {
    e.preventDefault()
    if (selectedId == null || !askText.trim() || askBusy) return
    setAskBusy(true)
    try {
      const { asks } = await apiAskMission(selectedId, askText.trim())
      setAskText('')
      setDetail((d) => (d ? { ...d, asks } : d))
    } catch (err) {
      capErr(err)
    } finally {
      setAskBusy(false)
    }
  }

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
                    placeholder="Qué quieres saber, para qué, restricciones…"
                    rows={5}
                    disabled={busy}
                  />
                </label>
                {modeField('cards')}
                <p className="muted missions__form-hint">
                  Primero un intake: varias preguntas para que el resultado no
                  vaya a ciegas. Luego revisas el brief y lanzas.
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
                <p className="missions__clarify-kicker">
                  Intake · ronda {round}
                </p>
                <h3 className="missions__clarify-lede">
                  {questions.length} pregunta
                  {questions.length === 1 ? '' : 's'} para afinar el encargo
                </h3>
                <p className="muted missions__form-hint">
                  Clic o escribe. Vacío = no aplica.
                </p>
                {modeField('pills')}
                {history.length > 0 ? (
                  <ol className="missions__asked">
                    {history.map((h, i) => (
                      <li key={`h-${i}`}>
                        <strong>{h.question}</strong>
                        <span>{h.answer || '—'}</span>
                      </li>
                    ))}
                  </ol>
                ) : null}
                <ol className="missions__qs">
                  {questions.map((q, i) => (
                    <li key={`${round}-${i}`} className="missions__q">
                      <label>
                        <span className="missions__q-n">
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        <span className="missions__q-text">{q.prompt}</span>
                      </label>
                      {q.choices.length > 0 ? (
                        <div
                          className="missions__q-choices"
                          role="group"
                          aria-label={q.prompt}
                        >
                          {q.choices.map((c) => {
                            const on = (picked[i] || '') === c
                            return (
                              <button
                                key={c}
                                type="button"
                                className={
                                  'missions__q-choice' + (on ? ' is-on' : '')
                                }
                                disabled={busy}
                                aria-pressed={on}
                                onClick={() => {
                                  setPicked((prev) => {
                                    const next = [...prev]
                                    next[i] = on ? '' : c
                                    return next
                                  })
                                }}
                              >
                                {c}
                              </button>
                            )
                          })}
                        </div>
                      ) : null}
                      <textarea
                        value={answers[i] ?? ''}
                        onChange={(e) => {
                          const next = [...answers]
                          next[i] = e.target.value
                          setAnswers(next)
                        }}
                        rows={q.choices.length > 0 ? 2 : 3}
                        disabled={busy}
                        placeholder={
                          q.choices.length > 0
                            ? q.allow_other
                              ? 'Detalle u otra respuesta'
                              : 'Detalle (opcional)'
                            : 'Tu respuesta'
                        }
                      />
                    </li>
                  ))}
                </ol>
                <div className="missions__form-actions">
                  <button type="submit" disabled={busy}>
                    {busy ? '…' : 'Seguir'}
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
                <p className="missions__clarify-kicker">Brief</p>
                <h3 className="missions__clarify-lede">
                  Listo para lanzar. Revisa que esté todo.
                </h3>
                <p className="muted missions__form-hint">
                  El encargo incluye todas las respuestas. Recorta solo si sobra.
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
                    rows={16}
                    disabled={busy}
                  />
                </label>
                {modeField('pills')}
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
                      setPicked([])
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
              Ninguna misión. Nueva para lanzar una.
            </li>
          ) : (
            visible.map((m) => {
              const costLabel = missionListCost(m)
              return (
              <li key={m.id}>
                <button
                  type="button"
                  className={
                    selectedId === m.id
                      ? 'missions__item missions__item--active'
                      : 'missions__item'
                  }
                  onClick={() => {
                    setCreating(false)
                    setSelectedId(m.id)
                  }}
                >
                  <div className="missions__item-top">
                    <span className="missions__item-title">{m.title}</span>
                    {costLabel ? (
                      <span
                        className={
                          m.status === 'done'
                            ? 'missions__item-cost'
                            : 'missions__item-cost missions__item-cost--partial'
                        }
                      >
                        {costLabel}
                      </span>
                    ) : null}
                  </div>
                  <span className="missions__item-meta muted">
                    {STATUS_LABEL[m.status] || m.status}
                    <span
                      className={
                        'missions__mode-tag missions__mode--' +
                        modeTone(missionModeId(m))
                      }
                    >
                      {missionModeLabel(m, modeOptions)}
                    </span>
                    {isActiveStatus(m.status) || m.status === 'done'
                      ? ` · ${missionProgressLabel(m) || `${m.step_index}/${m.max_ticks}`}`
                      : ''}
                  </span>
                </button>
              </li>
              )
            })
          )}
        </ul>
      </div>

      {panelOpen ? (
        <aside
          ref={panelRef}
          className="missions__panel"
          aria-label="Resumen de misión"
        >
          <div className="missions__panel-bar">
            <button
              type="button"
              className="ghost missions__panel-close"
              onClick={closePanel}
            >
              ← Lista
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
                <p className="muted missions__panel-meta">
                  {STATUS_LABEL[detail.status] || detail.status}
                  <span
                    className={
                      'missions__mode-tag missions__mode--' +
                      modeTone(missionModeId(detail))
                    }
                  >
                    {missionModeLabel(detail, modeOptions)}
                  </span>
                  {detail.model ? ` · ${detail.model.split('/').pop()}` : ''}
                  {isActiveStatus(detail.status) || detail.status === 'done'
                    ? ` · ${missionProgressLabel(detail) || `tick ${detail.step_index}/${detail.max_ticks}`}`
                    : ''}
                </p>
              </header>
              {detail.plan?.tasks?.length ? (
                <ol className="missions__tasks">
                  {detail.plan.tasks.map((t, i) => (
                    <li
                      key={`${detail.id}-${i}-${t.title}`}
                      className={
                        t.status === 'done'
                          ? 'missions__task missions__task--done'
                          : t.status === 'running'
                            ? 'missions__task missions__task--active'
                            : t.status === 'failed'
                              ? 'missions__task missions__task--failed'
                              : 'missions__task'
                      }
                    >
                      <span className="missions__task-mark" aria-hidden>
                        {taskStatusMark(t.status)}
                      </span>
                      <span className="missions__task-body">
                        <strong>{t.title}</strong>
                        {!isDoneStatus(detail.status) && t.goal ? (
                          <span className="muted missions__task-goal">{t.goal}</span>
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ol>
              ) : null}
              {detail.plan?.cost && detail.plan.cost.usd > 0 ? (
                <p className="missions__cost muted">
                  Gasto LLM:{' '}
                  <strong>{formatMissionCost(detail.plan.cost)}</strong>
                  {' · '}
                  {detail.plan.cost.prompt_tokens.toLocaleString()} in /{' '}
                  {detail.plan.cost.completion_tokens.toLocaleString()} out
                  {detail.plan.cost.account_delta_usd != null &&
                  detail.plan.cost.account_delta_usd > 0
                    ? ` · cuenta +${formatMissionCost({
                        ...detail.plan.cost,
                        usd: detail.plan.cost.account_delta_usd,
                        estimated: false,
                      })}`
                    : ''}
                </p>
              ) : null}
              {md ? (
                <div className="missions__report">
                  {report.result ? (
                    <section className="missions__result" aria-label="Resultado">
                      <button
                        type="button"
                        className="ghost missions__result-copy"
                        onClick={() => void copyResult()}
                      >
                        Copiar
                      </button>
                      <div
                        ref={resultRef}
                        className="missions__md missions__md--result"
                        onCopy={onCopyResult}
                        dangerouslySetInnerHTML={{
                          __html: renderMissionMarkdown(report.result.body),
                        }}
                      />
                    </section>
                  ) : null}
                  {showFullResearch ? (
                    <section
                      className="missions__research"
                      aria-label="Investigación"
                    >
                      <h4 className="missions__research-heading">
                        Investigación
                      </h4>
                      <div
                        className="missions__md"
                        dangerouslySetInnerHTML={{
                          __html: renderMissionMarkdown(report.detailMarkdown),
                        }}
                      />
                    </section>
                  ) : null}
                  {showLiveResearch ? (
                    <div className="missions__research missions__research--live">
                      <p className="muted missions__live-label">
                        Investigando…
                      </p>
                      {report.research.map((sec) => (
                        <section
                          key={sec.title}
                          className="missions__research-block"
                        >
                          <div
                            className="missions__md missions__md--muted"
                            dangerouslySetInnerHTML={{
                              __html: renderMissionMarkdown(
                                sectionToMarkdown(sec),
                              ),
                            }}
                          />
                        </section>
                      ))}
                    </div>
                  ) : null}
                  {!report.result && !showLiveResearch ? (
                    <div
                      className="missions__md"
                      dangerouslySetInnerHTML={{
                        __html: renderMissionMarkdown(md),
                      }}
                    />
                  ) : null}
                </div>
              ) : (
                <p className="muted">Sin informe aún.</p>
              )}
              {md ? (
                <section className="missions__ask" aria-label="Preguntar">
                  {(detail.asks || []).length > 0 ? (
                    <ol className="missions__ask-log">
                      {(detail.asks || []).map((turn, i) => (
                        <li key={`${i}-${turn.q.slice(0, 32)}`}>
                          <p className="missions__ask-q">{turn.q}</p>
                          <div
                            className="missions__ask-a missions__md"
                            dangerouslySetInnerHTML={{
                              __html: renderMissionMarkdown(turn.a),
                            }}
                          />
                        </li>
                      ))}
                    </ol>
                  ) : null}
                  <form
                    className="missions__ask-form"
                    onSubmit={(e) => void onAsk(e)}
                  >
                    <input
                      value={askText}
                      onChange={(e) => setAskText(e.target.value)}
                      placeholder="Preguntar sobre este resultado…"
                      maxLength={2000}
                      disabled={askBusy}
                    />
                    <button
                      type="submit"
                      disabled={askBusy || !askText.trim()}
                    >
                      {askBusy ? '…' : 'Preguntar'}
                    </button>
                  </form>
                </section>
              ) : null}
            </>
          )}
        </aside>
      ) : null}
    </section>
  )
}
