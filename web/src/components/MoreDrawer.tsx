import { UsageChip } from './UsageChip'

type Props = {
  open: boolean
  onClose: () => void
  onOpenDocs: () => void
  onOpenMemory: () => void
  onOpenPalette: () => void
  onLogout: () => void
}

export function MoreDrawer({
  open,
  onClose,
  onOpenDocs,
  onOpenMemory,
  onOpenPalette,
  onLogout,
}: Props) {
  if (!open) return null

  return (
    <div className="drawer" role="dialog" aria-modal="true" aria-label="Más">
      <button
        type="button"
        className="drawer__backdrop"
        aria-label="Cerrar"
        onClick={onClose}
      />
      <aside className="drawer__panel drawer__panel--more">
        <header className="drawer__head">
          <h2>Más</h2>
          <button type="button" className="ghost" onClick={onClose}>
            Cerrar
          </button>
        </header>

        <section className="more-drawer__section">
          <h3 className="more-drawer__h">Gasto LLM</h3>
          <UsageChip variant="block" />
        </section>

        <section className="more-drawer__section">
          <h3 className="more-drawer__h">Herramientas</h3>
          <ul className="more-drawer__actions">
            <li>
              <button
                type="button"
                className="more-drawer__btn"
                onClick={() => {
                  onClose()
                  onOpenMemory()
                }}
              >
                <span>Memoria / diario</span>
                <kbd>M</kbd>
              </button>
            </li>
            <li>
              <button
                type="button"
                className="more-drawer__btn"
                onClick={() => {
                  onClose()
                  onOpenDocs()
                }}
              >
                <span>Docs</span>
                <kbd>?</kbd>
              </button>
            </li>
            <li>
              <button
                type="button"
                className="more-drawer__btn"
                onClick={() => {
                  onClose()
                  onOpenPalette()
                }}
              >
                <span>Comandos</span>
                <kbd>⌘K</kbd>
              </button>
            </li>
          </ul>
        </section>

        <section className="more-drawer__section more-drawer__section--foot">
          <button
            type="button"
            className="more-drawer__btn more-drawer__btn--danger"
            onClick={() => {
              onClose()
              onLogout()
            }}
          >
            Salir
          </button>
        </section>
      </aside>
    </div>
  )
}
