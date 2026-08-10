import { useEffect, useState } from 'react'
import { apiGmailDisconnect, apiGmailStatus, type GmailStatus } from '../api'
import { LlmRoutingTable } from './LlmRoutingTable'
import { SpendLedgerPanel } from './SpendLedgerPanel'
import { UsageChip } from './UsageChip'

type Props = {
  open: boolean
  onClose: () => void
  onOpenDocs: () => void
  onOpenMemory: () => void
  onOpenSpend: () => void
  onOpenPalette: () => void
  onLogout: () => void
}

export function MoreDrawer({
  open,
  onClose,
  onOpenDocs,
  onOpenMemory,
  onOpenSpend,
  onOpenPalette,
  onLogout,
}: Props) {
  const [gmail, setGmail] = useState<GmailStatus | null>(null)
  const [gmailBusy, setGmailBusy] = useState(false)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    void apiGmailStatus().then((st) => {
      if (!cancelled) setGmail(st)
    })
    return () => {
      cancelled = true
    }
  }, [open])

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
          <SpendLedgerPanel
            variant="summary"
            onOpenDetail={() => {
              onClose()
              onOpenSpend()
            }}
          />
          <h3 className="more-drawer__h more-drawer__h--sub">Modelos</h3>
          <LlmRoutingTable />
        </section>

        <section className="more-drawer__section">
          <h3 className="more-drawer__h">Gmail</h3>
          {!gmail ? (
            <p className="muted">…</p>
          ) : !gmail.configured ? (
            <p className="muted">
              Falta <code>GOOGLE_CLIENT_*</code> en secrets.
            </p>
          ) : gmail.connected ? (
            <div className="more-drawer__gmail">
              <p className="more-drawer__gmail-email">{gmail.email || 'Conectado'}</p>
              {gmail.gmail_ready === false ? (
                <p className="more-drawer__gmail-hint muted">
                  Falta permiso de correo. Desconecta y vuelve a conectar para
                  autorizar Gmail.
                </p>
              ) : gmail.calendar_ready === false ? (
                <p className="more-drawer__gmail-hint muted">
                  Falta permiso de Calendar. Reconecta una vez para leer
                  eventos.
                </p>
              ) : gmail.calendar_can_write === false ? (
                <p className="more-drawer__gmail-hint muted">
                  Para crear bloques desde chat: reconecta y acepta editar
                  eventos de Calendar.
                </p>
              ) : gmail.can_send === false ? (
                <p className="more-drawer__gmail-hint muted">
                  Para responder mails: reconecta y acepta el permiso de envío.
                </p>
              ) : (
                <p className="more-drawer__gmail-hint muted">
                  Gmail + Calendar (lectura y escritura) conectados
                </p>
              )}
              <a className="more-drawer__btn" href="/api/gmail/connect">
                Reconectar
              </a>
              <button
                type="button"
                className="more-drawer__btn"
                disabled={gmailBusy}
                onClick={() => {
                  setGmailBusy(true)
                  void apiGmailDisconnect().then((ok) => {
                    setGmailBusy(false)
                    if (ok) {
                      setGmail({
                        ...gmail,
                        connected: false,
                        email: '',
                        gmail_ready: false,
                        can_send: false,
                        calendar_ready: false,
                        calendar_can_write: false,
                      })
                    }
                  })
                }}
              >
                Desconectar
              </button>
            </div>
          ) : (
            <a
              className="more-drawer__btn"
              href="/api/gmail/connect"
              onClick={onClose}
            >
              Conectar Gmail
            </a>
          )}
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
