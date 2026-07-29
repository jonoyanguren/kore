import { SpendLedgerPanel } from './SpendLedgerPanel'

type Props = {
  open: boolean
  onClose: () => void
}

export function SpendDrawer({ open, onClose }: Props) {
  if (!open) return null

  return (
    <div className="drawer" role="dialog" aria-modal="true" aria-label="Gasto LLM">
      <button
        type="button"
        className="drawer__backdrop"
        aria-label="Cerrar"
        onClick={onClose}
      />
      <aside className="drawer__panel drawer__panel--spend">
        <header className="drawer__head">
          <h2>Gasto LLM</h2>
          <button type="button" className="ghost" onClick={onClose}>
            Cerrar
          </button>
        </header>
        <p className="muted spend-drawer__lede">
          Ledger local de los últimos 7 días (chat, dream, misiones).
        </p>
        <SpendLedgerPanel variant="full" />
      </aside>
    </div>
  )
}
