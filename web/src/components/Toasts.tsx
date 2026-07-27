import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react'
import type { ReactNode } from 'react'

export type ToastKind = 'ok' | 'err' | 'info'

export type ToastItem = {
  id: number
  kind: ToastKind
  text: string
}

type ToastApi = {
  push: (kind: ToastKind, text: string, ms?: number) => void
  ok: (text: string) => void
  err: (text: string) => void
  info: (text: string) => void
}

const ToastContext = createContext<ToastApi | null>(null)

let seq = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const dismiss = useCallback((id: number) => {
    setItems((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (kind: ToastKind, text: string, ms = 3200) => {
      const id = ++seq
      setItems((prev) => [...prev.slice(-4), { id, kind, text }])
      window.setTimeout(() => dismiss(id), ms)
    },
    [dismiss],
  )

  const api = useMemo<ToastApi>(
    () => ({
      push,
      ok: (text) => push('ok', text, 2400),
      err: (text) => push('err', text, 5200),
      info: (text) => push('info', text, 4000),
    }),
    [push],
  )

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toasts" aria-live="polite" aria-relevant="additions">
        {items.map((t) => (
          <div key={t.id} className={`toast toast--${t.kind}`} role="status">
            <span>{t.text}</span>
            <button
              type="button"
              className="toast__x"
              aria-label="Cerrar"
              onClick={() => dismiss(t.id)}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast outside ToastProvider')
  }
  return ctx
}
