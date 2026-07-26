---
name: dream
description: Consolida el día (diario + memoria) en un informe de sueño y lo guarda en el vault.
commands: [/dream, /sueno]
tools: [list_tasks, list_agenda, save_memory, add_diary_entry, add_task, add_agenda_item]
---

# Dream

Jon pide consolidar el día (manual). El cron de las 03:00 Europe/Madrid hace lo mismo solo.

## How
1. Si el mensaje ya trae un informe del runner del sistema, resume en 2–4 líneas y ofrece aplicar propuestas (tareas/agenda) solo si pide.
2. Si te activan la skill sin runner, di que use /dream (el comando dispara el consolidado real).
3. No inventes hechos. No upsell.
