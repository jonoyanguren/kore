import { useEffect, useRef, useState } from 'react'
import { apiLogout } from '../api'
import { ChatPanel, type ChatPanelHandle } from './ChatPanel'
import {
  CommandPalette,
  type CommandAction,
} from './CommandPalette'
import { DayStrip } from './DayStrip'
import { TaskBoard, type TaskBoardHandle } from './TaskBoard'

type Props = {
  onLogout: () => void
}

export function Console({ onLogout }: Props) {
  const [boardToken, setBoardToken] = useState(0)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const chatRef = useRef<ChatPanelHandle>(null)
  const boardRef = useRef<TaskBoardHandle>(null)

  async function handleLogout() {
    await apiLogout()
    onLogout()
  }

  function bump() {
    setBoardToken((n) => n + 1)
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  function onCommand(action: CommandAction) {
    switch (action.kind) {
      case 'chat':
        chatRef.current?.run(action.text)
        break
      case 'focus_new_task':
        boardRef.current?.focusNewTask()
        break
      case 'filter_project':
        boardRef.current?.filterProject(action.project)
        break
      case 'clear_filters':
        boardRef.current?.clearFilters()
        break
      case 'logout':
        void handleLogout()
        break
    }
  }

  return (
    <div className="console">
      <header className="console__bar">
        <h1>Kore</h1>
        <div className="console__bar-actions">
          <button
            type="button"
            className="ghost console__cmdk-btn"
            onClick={() => setPaletteOpen(true)}
            title="⌘K"
          >
            ⌘K
          </button>
          <button type="button" className="ghost" onClick={() => void handleLogout()}>
            Salir
          </button>
        </div>
      </header>
      <DayStrip refreshToken={boardToken} />
      <div className="console__body">
        <ChatPanel
          ref={chatRef}
          onAfterChat={() => bump()}
          onOpenTask={(task) => boardRef.current?.openTask(task)}
        />
        <TaskBoard ref={boardRef} refreshToken={boardToken} />
      </div>
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onRun={onCommand}
      />
    </div>
  )
}
