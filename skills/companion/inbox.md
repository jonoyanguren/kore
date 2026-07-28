---
name: inbox
description: Correo Gmail — listar unread, marcar leído, mail→tarea.
commands: [/inbox]
tools: [list_inbox, mark_email_read, add_task]
---

# Inbox (Gmail)

Cuenta de Jon vía OAuth (`gmail.modify`). En la vista **Día** la lista unread
tiene botón **Tarea** (crea tarea con IA + link al mail) y **Leído**.

## How
1. `/inbox` → `list_inbox` y lista breve (asunto / de quién). Sin digests largos.
2. "márcalo leído" → `mark_email_read`.
3. "haz tarea de esto" → `add_task` con título corto + `url` = permalink.
4. Si no conectado → Más → Gmail.
5. No inventes mails. No envíes correo.
