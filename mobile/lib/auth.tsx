import * as SecureStore from 'expo-secure-store'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { apiMe } from './api'
import { SECRET_KEY } from './config'

type AuthState = {
  ready: boolean
  token: string | null
  login: (secret: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)
  const [token, setToken] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const stored = await SecureStore.getItemAsync(SECRET_KEY)
        if (cancelled) return
        if (!stored) {
          setReady(true)
          return
        }
        const ok = await apiMe(stored)
        if (cancelled) return
        if (ok) setToken(stored)
        else {
          setToken(null)
          try {
            await SecureStore.deleteItemAsync(SECRET_KEY)
          } catch {
            /* ignore */
          }
        }
      } catch {
        if (!cancelled) setToken(null)
      } finally {
        if (!cancelled) setReady(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (secret: string) => {
    const trimmed = secret.trim()
    if (!trimmed) throw new Error('Secret vacío')
    const ok = await apiMe(trimmed)
    if (!ok) throw new Error('Secret incorrecto')
    try {
      await SecureStore.setItemAsync(SECRET_KEY, trimmed)
    } catch {
      // Still allow session in memory if SecureStore fails (rare).
    }
    setToken(trimmed)
  }, [])

  const logout = useCallback(async () => {
    try {
      await SecureStore.deleteItemAsync(SECRET_KEY)
    } catch {
      /* ignore */
    }
    setToken(null)
  }, [])

  const value = useMemo(
    () => ({ ready, token, login, logout }),
    [ready, token, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth outside AuthProvider')
  return ctx
}
