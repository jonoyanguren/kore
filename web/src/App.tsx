import { useEffect, useState } from 'react'
import { apiMe } from './api'
import { Console } from './components/Console'
import { Landing } from './components/Landing'
import { Onboarding } from './components/Onboarding'
import { ToastProvider } from './components/Toasts'
import type { MeUser } from './types'
import './App.css'
import './Landing.css'

type Auth = 'loading' | 'out' | 'in'

function needsOnboarding(user: MeUser | null): boolean {
  if (user == null) return false
  if (user.legacy) return false
  return !user.onboarded
}

function App() {
  const [auth, setAuth] = useState<Auth>('loading')
  const [user, setUser] = useState<MeUser | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const me = await apiMe()
      if (cancelled) return
      if (me) {
        setUser(me)
        setAuth('in')
      } else {
        setUser(null)
        setAuth('out')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  function enter(next: MeUser | null) {
    setUser(next)
    setAuth('in')
  }

  let body
  if (auth === 'loading') {
    body = <main className="lp-boot" aria-busy="true" />
  } else if (auth === 'out') {
    body = <Landing onSuccess={enter} />
  } else if (needsOnboarding(user)) {
    body = (
      <Onboarding
        user={user as MeUser}
        onDone={(next) => setUser(next)}
      />
    )
  } else {
    body = (
      <Console
        companionName={user?.companion_name || 'Jone'}
        onUser={setUser}
        onLogout={() => {
          setUser(null)
          setAuth('out')
        }}
      />
    )
  }

  return <ToastProvider>{body}</ToastProvider>
}

export default App
