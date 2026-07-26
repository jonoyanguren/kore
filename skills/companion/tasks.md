---
name: tasks
description: Tareas locales del companion (lista, crear, completar) y agenda básica.
commands: [/tareas, /tasks, /agenda]
tools: [add_task, list_tasks, complete_task, add_agenda_item, list_agenda, resolve_madrid_date]
---

# Tasks & agenda

Sistema propio de Jon (no ClickUp). SQLite + export agenda en vault.

## How
1. Crear tarea → `add_task` (due_at YYYY-MM-DD vía `resolve_madrid_date` si habla natural).
2. Listar → `list_tasks` (open por defecto). Completar → `complete_task` con id.
3. Citas/recordatorios → `add_agenda_item` / `list_agenda`.
4. Confirma corto. Sin planes ni "si quieres…".
5. /tareas sin args puede ir por fast-path del bot; si hay args, actúa con tools.
