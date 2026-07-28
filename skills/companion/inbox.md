---
name: inbox
description: Correo Gmail — resumen de lo importante, listar unread, marcar leído, mail→tarea.
commands: [/inbox]
tools: [list_inbox, mark_email_read, add_task]
---

# Inbox (Gmail)

Cuenta de Jon vía OAuth (`gmail.modify`: leer + marcar leídas; **no** enviar).
La vista **Día** ya muestra un resumen IA del unread (caché ~30 min).

## How
1. `/inbox` o "qué hay en el correo" → `list_inbox` y **resume lo importante** (3–6 bullets). Ignora newsletters/ruido.
2. No vuelques la lista cruda salvo que Jon pida detalle o ids.
3. "márcalo leído" → `mark_email_read` con el `id`.
4. "haz tarea de esto" / mail accionable → `add_task` con título corto + `url` = permalink del mail.
5. Si `gmail_not_connected` / falta permiso → Más → Gmail (reconectar).
6. No inventes mails. No ofrezcas enviar correo.
