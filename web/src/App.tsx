import { useEffect, useState } from 'react'
import { apiMe } from './api'
import { Console } from './components/Console'
import { Landing } from './components/Landing'
import { Onboarding } from './components/Onboarding'
import { Paywall } from './components/Paywall'
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

function needsPaywall(user: MeUser | null): boolean {
  if (user == null) return false
  return Boolean(user.billing?.needed)
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

  useEffect(() => {
    if (auth !== 'in') return
    const params = new URLSearchParams(window.location.search)
    const flag = params.get('billing')
    if (flag !== 'ok' && flag !== 'cancel') return
    params.delete('billing')
    const qs = params.toString()
    window.history.replaceState({}, '', qs ? `/?${qs}` : '/')
    if (flag !== 'ok') return
    let cancelled = false
    ;(async () => {
      for (let i = 0; i < 10; i++) {
        const me = await apiMe()
        if (cancelled) return
        if (me) {
          setUser(me)
          if (!me.billing?.needed) return
        }
        await new Promise((r) => setTimeout(r, 600))
      }
    })()
    return () => {
      cancelled = true
    }
  }, [auth])

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
  } else if (needsPaywall(user)) {
    body = <Paywall user={user as MeUser} />
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
