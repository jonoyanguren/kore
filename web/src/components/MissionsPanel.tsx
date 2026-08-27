import { useEffect, useMemo, useRef, useState, type ClipboardEvent, type FormEvent } from 'react'
import {
  apiCancelMission,
  apiClarifyMission,
  apiCreateMission,
  apiGetMission,
  apiListMissions,
  apiMissionModeOptions,
  apiRelaunchMission,
  type ClarifyHistoryItem,
} from '../api'
import { cleanCopiedText, copyToClipboard } from '../lib/clipboard'
import { renderMissionMarkdown } from '../lib/missionMarkdown'
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

function missionListCost(m: Mission): string | null {
  const cost = m.plan?.cost
  if (!cost || cost.usd <= 0) return null
  return formatMissionCost(cost)
}

const FALLBACK_MODES: MissionModeOption[] = [
  {
    id: 'normal',
    label: 'Normal',
    when: 'Mira esto y dime qué harías',
    legend: 'Investiga y decide. Default.',
    blurb: 'Flash — barato y rápido',
    model: '',
    approx_usd: 0.04,
    approx_label: '~$0.02–0.06',
  },
  {
    id: 'loco',
    label: 'Loco',
    when: 'Quieres volumen y rareza, no la opción sensata',
    legend: 'Volumen y rareza; mapa, no una decisión.',
    blurb: 'Pro — divergente',
    model: '',
    approx_usd: 0.2,
    approx_label: '~$0.10–0.30',
  },
  {
    id: 'experto',
    label: 'Experto',
    when: 'Ya sabes el básico; quieres rigor',
    legend: 'Rigor; asume que ya sabes el básico.',
    blurb: 'Pro — profundo',
    model: '',
    approx_usd: 0.2,
    approx_label: '~$0.10–0.30',
  },
  {
    id: 'duro',
    label: 'Duro',
    when: 'Quieres que te tumben la idea',
    legend: 'Te tumba la idea; peor caso, cero ánimo.',
    blurb: 'Pro — red team',
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
  if (id === 'pro') return 'Experto'
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
  const [questions, setQuestions] = useState<string[]>([])
  const [answers, setAnswers] = useState<string[]>([])
  const [history, setHistory] = useState<ClarifyHistoryItem[]>([])
  const [round, setRound] = useState(1)
  const [refinedBrief, setRefinedBrief] = useState('')
  const [mode, setMode] = useState<MissionMode>('normal')
  const [modeOptions, setModeOptions] =
    useState<MissionModeOption[]>(FALLBACK_MODES)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const toast = useToast()
  const resultRef = useRef<HTMLDivElement>(null)

  const panelOpen = selectedId != null
  const selectedMode =
    modeOptions.find((o) => o.id === mode) || FALLBACK_MODES[0]

  function resetForm() {
    setTitle('')
    setBrief('')
    setPhase('draft')
    setQuestions([])
    setAnswers([])
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
      mode,
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
        tick_seconds: 10,
        mode,
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

  function modeField(variant: 'cards' | 'pills' = 'cards') {
    const approx = selectedMode.approx_label
    return (
      <div className="missions__mode">
        <span className="missions__mode-label" id="missions-mode-label">
          Modo
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
          {variant === 'cards' ? selectedMode.when : selectedMode.legend}
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
                {modeField('cards')}
                <p className="muted missions__form-hint">
                  Plan automático → tareas en secuencia con handoff entre pasos.
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
                {modeField('pills')}
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
                  onClick={() => setSelectedId(m.id)}
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
            </>
          )}
        </aside>
      ) : null}
    </section>
  )
}
