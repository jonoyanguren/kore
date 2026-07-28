---
name: inbox
description: Correo Gmail (listar unread/hoy, marcar leído). Scope gmail.modify.
commands: [/inbox]
tools: [list_inbox, mark_email_read]
---

# Inbox (Gmail)

Cuenta de Jon vía OAuth (`gmail.modify`: leer + marcar leídas; **no** enviar).

## How
1. `/inbox` o "qué hay en el correo" → `list_inbox` (default `is:unread newer_than:1d`).
2. Resume corto: de quién, asunto, una línea. Link si ayuda.
3. "márcalo leído" / "ya lo vi" → `mark_email_read` con el `id` de `list_inbox`.
4. Si `gmail_not_connected` → di que conecte desde **Más → Gmail** en la consola.
5. No inventes mails. No ofrezcas enviar correo (aún no hay tool de send).
6. Queries útiles: `is:unread`, `newer_than:1d`, `from:foo@bar.com`, `subject:…`.
