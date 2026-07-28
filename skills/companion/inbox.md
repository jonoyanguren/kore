---
name: inbox
description: Correo Gmail — listar unread, marcar leído, log de triage, mail→tarea, reply desde Día.
commands: [/inbox]
tools: [list_inbox, mark_email_read, list_marked_read, add_task]
---

# Inbox (Gmail)

Cuenta de Jon vía OAuth (`gmail.modify` + `gmail.send`). En la vista **Día**: lista
unread con **Responder** / **Tarea** / **Leído**, más “Marcados leídos hoy”.

**Responder (D17):** lee el mail → propone borrador editable → Jon confirma → envía.
No envíes correo desde el chat; el envío es solo desde Día tras confirmar.

## How
1. `/inbox` → `list_inbox` y lista breve (asunto / de quién).
2. "márcalo leído" → `mark_email_read` (queda en el log de triage).
3. "qué marcaste leído" / "triage" → `list_marked_read` (hoy por defecto).
4. "haz tarea de esto" → `add_task` con título corto + `url` = permalink.
5. Responder un mail → Jon usa **Responder** en Día (no tools de send).
6. Si no conectado / falta send → Más → Gmail (reconectar).
7. No inventes mails. No envíes correo por tu cuenta.
