---
name: tasks
description: Tareas locales del companion (lista, crear, completar, links, estados, proyecto).
commands: [/tareas, /tasks, /agenda]
tools: [add_task, list_tasks, get_task, update_task, complete_task, delete_task, add_agenda_item, list_agenda, resolve_madrid_date]
---

# Tasks & agenda

Sistema propio de Jon (no ClickUp).

**Dónde se guarda:** tabla SQLite `tasks` en la DB del companion
(Fly: `/data/kore.db`; local: `data/kore.db`). Mirror legible: `vault/tasks/open.md`.
No es `docs/TODO.md` (eso es backlog de desarrollo Kore en git).

## Campos
- title (corto)
- status: `open` | `in_progress` | `done` | `cancelled`
- due_at: YYYY-MM-DD
- project: slug (`kore`, `personal`, `kimay`, `lol`, …)
- url: link si el usuario pegó o mencionó uno (Instagram, YouTube, doc…)
- notes: contexto extra

## How
1. Crear → `add_task` **obligatorio** antes de decir "creada/añadida". Sin tool = no digas que está hecha.
2. "en curso" / "importante" → `status=in_progress` o `priority` alta; proyecto si se deduce.
3. Listar → `list_tasks` **solo si Jon pide la lista** (o necesitas ids para editar). En consola web el board ya muestra tareas: no vuelques un listado completo en cada respuesta.
4. Editar link/nota/estado → `update_task`. Borrar → `delete_task`. Hecha → `complete_task`.
5. Fechas naturales → `resolve_madrid_date` → due_at ISO.
6. Confirma corto mostrando id + link si existe. Sin upsell.
7. `/tareas` (Telegram) = lista rápida; chat libre = tools solo cuando toca.
8. Duplicados: busca con `list_tasks` y `delete_task` / fusiona con `update_task`, no crees otra igual.
