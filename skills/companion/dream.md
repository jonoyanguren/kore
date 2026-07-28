---
name: dream
description: Revisa el chat del día, rellena huecos (memoria/diario/agenda), mira Gmail unread y deja briefing en vista Día.
commands: [/dream, /sueno]
tools: [save_memory, add_diary_entry, complete_task, delete_task, list_tasks, get_task, update_task, add_agenda_item, list_agenda]
---

# Dream (briefing matutino)

Cron in-process **09:00 Europe/Madrid** (Fly, asyncio). Manual `/dream` → por defecto **hoy**.
`POST /internal/cron/dream` queda como trigger opcional.
Modelo: **strong** (`OPENROUTER_MODEL_STRONG`, default Haiku 4.5; alt Kimi/Sonnet).

## Qué hace el runner (no improvisar a mano)
1. Carga el transcript del día + diario/memoria/tareas abiertas + `done.md` (archivo).
2. Carga unread Gmail (si OAuth OK) y pide sección **Inbox** en el briefing.
3. Con tools: memoria/diario/agenda; puede completar/actualizar tareas **ya existentes**.
4. **No** `add_task` — no resucita archivadas ni inventa pendientes del chat/mail.
5. Escribe `vault/dreams/YYYY-MM-DD.md`.
6. La consola Día usa tareas+agenda vivas + secciones parseadas del dream (incl. Inbox).

## How (si te activan la skill en chat)
Si el comando `/dream` ya corrió el runner, no rehagas el trabajo: el mensaje ya es el informe.
Si te piden sueño en prosa sin comando, dile que use `/dream`.
