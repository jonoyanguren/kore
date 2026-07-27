import { useEffect, useState } from 'react'
import { apiMe } from './api'
import { Console } from './components/Console'
import { Login } from './components/Login'
import { ToastProvider } from './components/Toasts'
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

  let body
  if (auth === 'loading') {
    body = (
      <main className="login">
        <p className="muted">…</p>
      </main>
    )
  } else if (auth === 'out') {
    body = <Login onSuccess={() => setAuth('in')} />
  } else {
    body = <Console onLogout={() => setAuth('out')} />
  }

  return <ToastProvider>{body}</ToastProvider>
}

export default App
