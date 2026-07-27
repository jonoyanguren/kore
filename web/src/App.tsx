import { useEffect, useState } from 'react'
import { apiMe } from './api'
import { Login } from './components/Login'
import { TaskBoard } from './components/TaskBoard'
import './App.css'

type Auth = 'loading' | 'in' | 'out'

function App() {
  const [auth, setAuth] = useState<Auth>('loading')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const ok = await apiMe()
      if (!cancelled) setAuth(ok ? 'in' : 'out')
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (auth === 'loading') {
    return (
      <main className="login">
        <p className="muted">…</p>
      </main>
    )
  }

  if (auth === 'out') {
    return <Login onSuccess={() => setAuth('in')} />
  }

  return <TaskBoard onLogout={() => setAuth('out')} />
}

export default App
