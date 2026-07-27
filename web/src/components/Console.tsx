import { useState } from 'react'
import { apiLogout } from '../api'
import { ChatPanel } from './ChatPanel'
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

  return (
    <div className="console">
      <header className="console__bar">
        <h1>Kore</h1>
        <button type="button" className="ghost" onClick={() => void handleLogout()}>
          Salir
        </button>
      </header>
      <div className="console__body">
        <ChatPanel onAfterChat={() => setBoardToken((n) => n + 1)} />
        <TaskBoard refreshToken={boardToken} />
      </div>
    </div>
  )
}
