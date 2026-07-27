import { useState } from 'react'
import { apiLogout } from '../api'
import { ChatPanel } from './ChatPanel'
import { DayStrip } from './DayStrip'
import { TaskBoard } from './TaskBoard'

type Props = {
  onLogout: () => void
}

export function Console({ onLogout }: Props) {
  const [boardToken, setBoardToken] = useState(0)

  async function handleLogout() {
    await apiLogout()
    onLogout()
  }

  function bump() {
    setBoardToken((n) => n + 1)
  }

  return (
    <div className="console">
      <header className="console__bar">
        <h1>Kore</h1>
        <button type="button" className="ghost" onClick={() => void handleLogout()}>
          Salir
        </button>
      </header>
      <DayStrip refreshToken={boardToken} />
      <div className="console__body">
        <ChatPanel onAfterChat={() => bump()} />
        <TaskBoard refreshToken={boardToken} />
      </div>
    </div>
  )
}
