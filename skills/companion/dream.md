---
name: dream
description: Revisa el chat del día, rellena huecos (memoria/diario/tareas) y manda briefing + prep del día siguiente.
commands: [/dream, /sueno]
tools: [save_memory, add_diary_entry, add_task, complete_task, delete_task, list_tasks, get_task, update_task, add_agenda_item, list_agenda]
---

# Dream (briefing matutino)

Cron externo ~**09:00 Europe/Madrid** → `POST /internal/cron/dream` (consolida el **día anterior**).
Manual `/dream` → por defecto **hoy** (o `YYYY-MM-DD` en args).

## Qué hace el runner (no improvisar a mano)
1. Carga el transcript completo de `messages` de ese día + diario/memoria/tareas/agenda.
2. Con tools, anota lo que se le pasó en el chat.
3. Escribe `vault/dreams/YYYY-MM-DD.md`.
4. Envía a Jon (plantilla fija): **Resumen / Tareas importantes / Reuniones / Ayuda / Cierre**.
5. La consola Día usa tareas+agenda vivas + sección **Ayuda** parseada del dream.

## How (si te activan la skill en chat)
Si el comando `/dream` ya corrió el runner, no rehagas el trabajo: el mensaje ya es el informe.
Si te piden sueño en prosa sin comando, dile que use `/dream`.
