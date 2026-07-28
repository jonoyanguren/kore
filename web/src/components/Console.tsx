import { useEffect, useRef, useState } from 'react'
import { apiLogout } from '../api'
import { ChatPanel, type ChatPanelHandle } from './ChatPanel'
import {
  CommandPalette,
  type CommandAction,
} from './CommandPalette'
import { DayStrip } from './DayStrip'
import { DocsDrawer, type DocsSectionId } from './DocsDrawer'
import { MemoryDrawer } from './MemoryDrawer'
import { MoreDrawer } from './MoreDrawer'
import { TaskBoard, type TaskBoardHandle } from './TaskBoard'
import type { Task } from '../types'

export type LayoutMode = 'day' | 'focus' | 'operate'

const LAYOUTS: { id: LayoutMode; label: string }[] = [
  { id: 'day', label: 'Día' },
  { id: 'focus', label: 'Chat' },
  { id: 'operate', label: 'Board' },
]

const STORAGE_KEY = 'kore.layout'
/** Default accent (no space chips). */
const ACCENT = '#2f6f5e'

type Props = {
  onLogout: () => void
}

function readLayout(): LayoutMode {
  const v = localStorage.getItem(STORAGE_KEY)
  if (v === 'day' || v === 'focus' || v === 'operate') return v
  return 'day'
}

export function Console({ onLogout }: Props) {
  const [boardToken, setBoardToken] = useState(0)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const [memoryOpen, setMemoryOpen] = useState(false)
  const [memoryTab, setMemoryTab] = useState<'diary' | 'memory' | 'privacy'>(
    'diary',
  )
  const [docsOpen, setDocsOpen] = useState(false)
  const [docsSection, setDocsSection] = useState<DocsSectionId>('que-es')
  const [layout, setLayout] = useState<LayoutMode>(() => readLayout())
  const chatRef = useRef<ChatPanelHandle>(null)
  const boardRef = useRef<TaskBoardHandle>(null)

  async function handleLogout() {
    await apiLogout()
    onLogout()
  }

  function bump() {
    setBoardToken((n) => n + 1)
  }

  function setLayoutPersist(next: LayoutMode) {
    setLayout(next)
    localStorage.setItem(STORAGE_KEY, next)
  }

  function openMemory(tab: 'diary' | 'memory' | 'privacy' = 'diary') {
    setMemoryTab(tab)
    setMemoryOpen(true)
  }

  function openDocs(section: DocsSectionId = 'que-es') {
    setDocsSection(section)
    setDocsOpen(true)
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((v) => !v)
        return
      }
      const t = e.target as HTMLElement | null
      const typing =
        t &&
        (t.tagName === 'INPUT' ||
          t.tagName === 'TEXTAREA' ||
          t.isContentEditable)
      if (typing || e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key === '1') setLayoutPersist('day')
      if (e.key === '2') setLayoutPersist('focus')
      if (e.key === '3') setLayoutPersist('operate')
      if (e.key.toLowerCase() === 'm') openMemory('diary')
      if (e.key === '?' || e.key.toLowerCase() === 'h') openDocs()
      if (e.key === ',') setMoreOpen(true)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  function onOpenTask(task: Task) {
    setLayoutPersist('operate')
    window.setTimeout(() => boardRef.current?.openTask(task), 0)
  }

  function onCommand(action: CommandAction) {
    switch (action.kind) {
      case 'chat':
        setLayoutPersist('focus')
        window.setTimeout(() => chatRef.current?.run(action.text), 0)
        break
      case 'focus_new_task':
        setLayoutPersist('operate')
        window.setTimeout(() => boardRef.current?.focusNewTask(), 0)
        break
      case 'filter_project':
        setLayoutPersist('operate')
        window.setTimeout(
          () => boardRef.current?.filterProject(action.project),
          0,
        )
        break
      case 'clear_filters':
        setLayoutPersist('operate')
        window.setTimeout(() => boardRef.current?.clearFilters(), 0)
        break
      case 'layout':
        setLayoutPersist(action.mode)
        break
      case 'open_memory':
        openMemory(action.tab ?? 'diary')
        break
      case 'open_docs':
        openDocs(action.section ?? 'que-es')
        break
      case 'logout':
        void handleLogout()
        break
    }
  }

  return (
    <div
      className={`console console--${layout}`}
      style={{ ['--space-accent' as string]: ACCENT }}
    >
      <header className="console__bar">
        <div className="console__brand">
          <span className="console__mark">Kore</span>
        </div>
        <nav className="console__layouts" aria-label="Vista">
          {LAYOUTS.map((l) => (
            <button
              key={l.id}
              type="button"
              className={`console__layout${layout === l.id ? ' is-active' : ''}`}
              onClick={() => setLayoutPersist(l.id)}
            >
              {l.label}
            </button>
          ))}
        </nav>
        <div className="console__bar-actions">
          <button
            type="button"
            className="ghost console__more-btn"
            onClick={() => setMoreOpen(true)}
            title="Más (,)"
            aria-label="Más: gasto LLM, docs, memoria"
          >
            <svg
              className="console__more-icon"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <circle cx="12" cy="12" r="9" />
              <path d="M12 10.5v6" />
              <circle cx="12" cy="7.5" r="0.9" fill="currentColor" stroke="none" />
            </svg>
          </button>
        </div>
      </header>

      {layout === 'day' ? (
        <DayStrip
          refreshToken={boardToken}
          variant="hero"
          onOpenChat={() => setLayoutPersist('focus')}
          onOpenBoard={() => setLayoutPersist('operate')}
          onOpenMemory={() => openMemory('diary')}
        />
      ) : null}

      <div className="console__body">
        <ChatPanel
          ref={chatRef}
          onAfterChat={() => bump()}
          onOpenTask={onOpenTask}
        />
        <TaskBoard ref={boardRef} refreshToken={boardToken} />
      </div>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onRun={onCommand}
      />
      <MoreDrawer
        open={moreOpen}
        onClose={() => setMoreOpen(false)}
        onOpenDocs={() => openDocs()}
        onOpenMemory={() => openMemory('diary')}
        onOpenPalette={() => setPaletteOpen(true)}
        onLogout={() => void handleLogout()}
      />
      <MemoryDrawer
        open={memoryOpen}
        initialTab={memoryTab}
        onClose={() => setMemoryOpen(false)}
      />
      <DocsDrawer
        open={docsOpen}
        initialSection={docsSection}
        onClose={() => setDocsOpen(false)}
      />
    </div>
  )
}
