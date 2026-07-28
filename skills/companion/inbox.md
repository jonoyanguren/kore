---
name: inbox
description: Correo Gmail — listar unread, marcar leído, log de triage, mail→tarea.
commands: [/inbox]
tools: [list_inbox, mark_email_read, list_marked_read, add_task]
---

# Inbox (Gmail)

Cuenta de Jon vía OAuth (`gmail.modify`). En la vista **Día**: lista unread con
**Tarea** / **Leído**, más “Marcados leídos hoy” (log de triage).

## How
1. `/inbox` → `list_inbox` y lista breve (asunto / de quién).
2. "márcalo leído" → `mark_email_read` (queda en el log de triage).
3. "qué marcaste leído" / "triage" → `list_marked_read` (hoy por defecto).
4. "haz tarea de esto" → `add_task` con título corto + `url` = permalink.
5. Si no conectado → Más → Gmail.
6. No inventes mails. No envíes correo.
