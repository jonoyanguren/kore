import { useEffect, useState, type ReactNode } from 'react'

export type DocsSectionId =
  | 'que-es'
  | 'canales'
  | 'vistas'
  | 'tareas'
  | 'memoria'
  | 'sueno'
  | 'skills'
  | 'comandos'
  | 'atajos'

type CmdRow = { cmd: string; desc: string }
type SkillRow = { name: string; cmds: string[]; desc: string; tone?: string }
type KeyRow = { key: string; desc: string }

type Block =
  | { type: 'p'; text: string }
  | { type: 'h4'; text: string }
  | { type: 'ul'; items: string[] }
  | { type: 'callout'; tone: 'tip' | 'info' | 'warn'; text: string }
  | { type: 'cmds'; items: CmdRow[] }
  | { type: 'skills'; items: SkillRow[] }
  | { type: 'keys'; items: KeyRow[] }

type Section = {
  id: DocsSectionId
  title: string
  accent: string
  blocks: Block[]
}

/** Companion skills loaded by Jone (not Cursor dev/open|close). */
const COMPANION_SKILLS: SkillRow[] = [
  {
    name: 'tasks',
    cmds: ['/tareas', '/tasks', '/agenda'],
    desc: 'Tareas y agenda locales (crear, listar, completar, proyecto, links).',
    tone: 'green',
  },
  {
    name: 'dream',
    cmds: ['/dream', '/sueno'],
    desc: 'Consolida el día: chat → memoria/diario/tareas + briefing.',
    tone: 'violet',
  },
  {
    name: 'capture',
    cmds: ['/captura'],
    desc: 'Guarda hechos por categoría (memoria) o eventos del día (diario).',
    tone: 'blue',
  },
  {
    name: 'time-madrid',
    cmds: ['/hora'],
    desc: 'Hora y fechas en Europe/Madrid, en lenguaje natural.',
    tone: 'amber',
  },
  {
    name: 'brainstorm',
    cmds: ['/brainstorm'],
    desc: 'Explorar opciones en abierto — divergir sin cerrar ni ejecutar.',
    tone: 'rose',
  },
  {
    name: 'plan',
    cmds: ['/plan'],
    desc: 'Convertir contexto en plan por pasos (sin ejecutar aún).',
    tone: 'teal',
  },
  {
    name: 'execute',
    cmds: ['/execute'],
    desc: 'Avanzar el siguiente paso concreto del plan o petición.',
    tone: 'orange',
  },
  {
    name: 'project-status',
    cmds: ['/estado', '/next'],
    desc: 'Qué toca del proyecto Kore según PLAN/TODO.',
    tone: 'slate',
  },
]

const CHAT_COMMANDS: CmdRow[] = [
  { cmd: '/tareas', desc: 'Lista tareas abiertas (+ en curso)' },
  { cmd: '/agenda', desc: 'Próximos eventos de agenda' },
  { cmd: '/dream', desc: 'Sueño / briefing del día' },
  { cmd: '/sueno', desc: 'Alias de /dream' },
  { cmd: '/captura', desc: 'Guardar en memoria o diario' },
  { cmd: '/diario', desc: 'Ver / añadir diario del día' },
  { cmd: '/hora', desc: 'Hora actual en Madrid' },
  { cmd: '/brainstorm', desc: 'Modo brainstorm' },
  { cmd: '/plan', desc: 'Modo plan' },
  { cmd: '/execute', desc: 'Modo execute' },
  { cmd: '/estado', desc: 'Estado del proyecto Kore' },
  { cmd: '/next', desc: 'Alias de /estado' },
  { cmd: '/skills', desc: 'Listar skills cargadas' },
  { cmd: '/start', desc: 'Saludo + comandos básicos' },
]

const SECTIONS: Section[] = [
  {
    id: 'que-es',
    title: 'Qué es Kore',
    accent: 'teal',
    blocks: [
      {
        type: 'p',
        text: '**Kore** es tu compañero personal. En el chat habla como **Jone**: tuteo, directo, sin postureo.',
      },
      {
        type: 'callout',
        tone: 'tip',
        text: 'No es solo un chatbot: captura hechos, tareas y agenda, y por la mañana te deja un briefing.',
      },
      {
        type: 'ul',
        items: [
          'Consola web → operar (board, checks, día, memoria)',
          'Telegram → captura rápida en el móvil',
          'Misma base: SQLite + vault en Fly',
        ],
      },
    ],
  },
  {
    id: 'canales',
    title: 'Canales',
    accent: 'blue',
    blocks: [
      {
        type: 'h4',
        text: 'Telegram',
      },
      {
        type: 'p',
        text: 'Comandos `/tareas`, `/dream`, `/agenda`… Ideal para captura al vuelo.',
      },
      {
        type: 'h4',
        text: 'Consola web',
      },
      {
        type: 'p',
        text: 'Mismo cerebro, mejor para board, filtros, checks y ver el día de un vistazo.',
      },
      {
        type: 'callout',
        tone: 'info',
        text: 'Lo que cambias en un canal se refleja en el otro.',
      },
    ],
  },
  {
    id: 'vistas',
    title: 'Vistas',
    accent: 'violet',
    blocks: [
      {
        type: 'ul',
        items: [
          '**Día** — briefing, tareas importantes, reuniones, ayuda del dream',
          '**Chat** — hablar con Jone (texto; voz más adelante)',
          '**Board** — tareas en lista o columnas',
        ],
      },
      {
        type: 'callout',
        tone: 'tip',
        text: 'Atajos: `1` Día · `2` Chat · `3` Board',
      },
    ],
  },
  {
    id: 'tareas',
    title: 'Tareas',
    accent: 'green',
    blocks: [
      {
        type: 'h4',
        text: 'Estados',
      },
      {
        type: 'ul',
        items: [
          'Sin marca → **pendiente**',
          '`✓` check → **hecha** (tachada)',
          '`★` estrella → **en curso**',
        ],
      },
      {
        type: 'h4',
        text: 'Lista / Board',
      },
      {
        type: 'p',
        text: 'Toggle arriba. Arrastra (`⋮⋮` en lista) para reordenar; el orden se **guarda**.',
      },
      {
        type: 'callout',
        tone: 'info',
        text: '«Archivar completadas» las quita de la UI/BD y las guarda en `vault/tasks/done.md` para contexto de Jone.',
      },
      {
        type: 'p',
        text: 'También puedes crear/mover tareas hablando con Jone (`/tareas` o chat libre).',
      },
    ],
  },
  {
    id: 'memoria',
    title: 'Memoria y diario',
    accent: 'amber',
    blocks: [
      {
        type: 'ul',
        items: [
          '**Diario** — notas del día (lo que pasó hoy)',
          '**Memoria** — hechos por categoría que Jone reutiliza',
        ],
      },
      {
        type: 'callout',
        tone: 'tip',
        text: 'Botón Memoria o tecla `M`. En chat: `/diario` y `/captura` / «recuerda…».',
      },
    ],
  },
  {
    id: 'sueno',
    title: 'Sueño (~09:00)',
    accent: 'violet',
    blocks: [
      {
        type: 'p',
        text: 'Cada mañana a las **09:00 Europe/Madrid** el cron consolida el **día anterior** y deja el briefing en la **vista Día** de esta consola (canal principal). Telegram es opcional (`DREAM_NOTIFY_TELEGRAM`).',
      },
      {
        type: 'ul',
        items: [
          'Mañana: abre https://kore.fly.dev/ → vista **Día** (Resumen / Tareas / Reuniones / Ayuda)',
          'Chat de la consola: `/dream` si quieres forzar a mano',
          'Captura rápida en móvil: Telegram sigue disponible, pero no es obligatorio',
        ],
      },
    ],
  },
  {
    id: 'skills',
    title: 'Skills',
    accent: 'rose',
    blocks: [
      {
        type: 'p',
        text: 'Playbooks que carga **Jone** en Telegram/chat. Cada skill trae comandos y tools.',
      },
      {
        type: 'callout',
        tone: 'info',
        text: 'Las skills `dev/open` y `dev/close` son solo para Cursor (desarrollo Kore), no van al bot.',
      },
      { type: 'skills', items: COMPANION_SKILLS },
    ],
  },
  {
    id: 'comandos',
    title: 'Comandos',
    accent: 'blue',
    blocks: [
      {
        type: 'h4',
        text: 'En chat / Telegram',
      },
      { type: 'cmds', items: CHAT_COMMANDS },
      {
        type: 'h4',
        text: 'Paleta ⌘K',
      },
      {
        type: 'ul',
        items: [
          'Cambiar vista Día / Chat / Board',
          'Abrir Docs, Memoria, Sueño, Hora, Agenda',
          'Nueva tarea · filtrar por proyecto · salir',
        ],
      },
      {
        type: 'callout',
        tone: 'tip',
        text: '`⌘K` / `Ctrl+K` abre la paleta. `/skills` lista lo cargado en el bot.',
      },
    ],
  },
  {
    id: 'atajos',
    title: 'Atajos',
    accent: 'slate',
    blocks: [
      {
        type: 'keys',
        items: [
          { key: '1', desc: 'Vista Día' },
          { key: '2', desc: 'Vista Chat' },
          { key: '3', desc: 'Vista Board' },
          { key: 'M', desc: 'Memoria / diario' },
          { key: '?', desc: 'Docs (también H)' },
          { key: '⌘K', desc: 'Command palette' },
          { key: 'Esc', desc: 'Cerrar drawer' },
        ],
      },
      {
        type: 'callout',
        tone: 'warn',
        text: 'Los atajos de una tecla no aplican si estás escribiendo en un input.',
      },
    ],
  },
]

function renderInline(text: string): ReactNode[] {
  const parts: ReactNode[] = []
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let last = 0
  let m: RegExpExecArray | null
  let k = 0
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    const token = m[0]
    if (token.startsWith('**')) {
      parts.push(
        <strong key={k++} className="docs-md__strong">
          {token.slice(2, -2)}
        </strong>,
      )
    } else {
      parts.push(
        <code key={k++} className="docs-md__code">
          {token.slice(1, -1)}
        </code>,
      )
    }
    last = m.index + token.length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

function BlockView({ block }: { block: Block }) {
  switch (block.type) {
    case 'p':
      return <p className="docs-md__p">{renderInline(block.text)}</p>
    case 'h4':
      return <h4 className="docs-md__h4">{block.text}</h4>
    case 'ul':
      return (
        <ul className="docs-md__ul">
          {block.items.map((item) => (
            <li key={item}>{renderInline(item)}</li>
          ))}
        </ul>
      )
    case 'callout':
      return (
        <aside className={`docs-md__callout docs-md__callout--${block.tone}`}>
          {renderInline(block.text)}
        </aside>
      )
    case 'cmds':
      return (
        <ul className="docs-md__cmd-list">
          {block.items.map((row) => (
            <li key={row.cmd}>
              <code className="docs-md__cmd">{row.cmd}</code>
              <span>{row.desc}</span>
            </li>
          ))}
        </ul>
      )
    case 'skills':
      return (
        <div className="docs-md__skills">
          {block.items.map((s) => (
            <article
              key={s.name}
              className={`docs-md__skill docs-md__skill--${s.tone ?? 'slate'}`}
            >
              <header>
                <span className="docs-md__skill-name">{s.name}</span>
                <span className="docs-md__skill-cmds">
                  {s.cmds.map((c) => (
                    <code key={c}>{c}</code>
                  ))}
                </span>
              </header>
              <p>{s.desc}</p>
            </article>
          ))}
        </div>
      )
    case 'keys':
      return (
        <ul className="docs-md__keys">
          {block.items.map((row) => (
            <li key={row.key}>
              <kbd>{row.key}</kbd>
              <span>{row.desc}</span>
            </li>
          ))}
        </ul>
      )
  }
}

type Props = {
  open: boolean
  onClose: () => void
  initialSection?: DocsSectionId
}

export function DocsDrawer({
  open,
  onClose,
  initialSection = 'que-es',
}: Props) {
  const [section, setSection] = useState<DocsSectionId>(initialSection)

  useEffect(() => {
    if (!open) return
    setSection(initialSection)
  }, [open, initialSection])

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const current = SECTIONS.find((s) => s.id === section) ?? SECTIONS[0]

  return (
    <div className="drawer" role="dialog" aria-modal="true" aria-label="Docs">
      <button
        type="button"
        className="drawer__backdrop"
        aria-label="Cerrar"
        onClick={onClose}
      />
      <aside className="drawer__panel drawer__panel--docs">
        <header className="drawer__head">
          <h2>Cómo funciona</h2>
          <button type="button" className="ghost" onClick={onClose}>
            Cerrar
          </button>
        </header>
        <p className="docs-drawer__lede muted">
          Kore · Jone · guía con skills y comandos
        </p>
        <div className="docs-drawer__layout">
          <nav className="docs-drawer__nav" aria-label="Secciones">
            {SECTIONS.map((s) => (
              <button
                key={s.id}
                type="button"
                className={`docs-nav__btn docs-nav__btn--${s.accent}${s.id === current.id ? ' is-active' : ''}`}
                onClick={() => setSection(s.id)}
              >
                {s.title}
              </button>
            ))}
          </nav>
          <article
            className={`docs-drawer__body docs-drawer__body--${current.accent}`}
          >
            <h3 className="docs-md__title">{current.title}</h3>
            {current.blocks.map((b, i) => (
              <BlockView key={`${current.id}-${i}`} block={b} />
            ))}
          </article>
        </div>
      </aside>
    </div>
  )
}
