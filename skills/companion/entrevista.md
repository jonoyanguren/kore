---
name: entrevista
description: Rellenar información con preguntas (comando = entrevista; chat = max 1 Q).
commands: [/entrevista, /interview]
tools: [save_memory, add_diary_entry, list_tasks, get_task, update_task, add_task, list_agenda, add_agenda_item, resolve_madrid_date, get_madrid_time]
---

# Entrevista

Dos modos. No los mezcles.

## Modo A — comando `/entrevista` (o `/interview`)

Jon abre una **entrevista**: rellenas huecos con preguntas cortas.

1. Mira lo que ya dijo (args del comando + historial reciente) y elige el **siguiente hueco más útil** (fecha, gente, URL, presupuesto, decisión, zona…).
2. Haz **una sola pregunta** por turno. Corta, concreta, en español.
3. Cuando responda algo útil → guarda con tools si aplica (`save_memory`, `update_task`, agenda…) → confirma en una línea → siguiente pregunta.
4. Máximo ~5 preguntas por sesión. Si ya hay bastante, cierra.
5. **Salidas:** si dice “basta”, “listo”, “para”, “ya está” → para, resume en 1–3 líneas qué quedó apuntado, STOP.
6. No inventes datos. No lances planes largos ni misiones en este modo.

## Modo B — chat normal (sin `/entrevista`)

Este playbook está siempre disponible, pero **no** conviertas el chat en entrevista.

- Solo pregunta si Jon pide guardar/actuar y falta un dato **sin el cual no se puede**, o hay ambigüedad que cambiaría la acción.
- **Máximo una pregunta.** Luego STOP (responde o captura; no encadenes).
- Si capture/tarea ya pueden cerrar sin ese dato → no preguntes (preferir `capture` STOP).
- Nunca espontáneamente 3–5 preguntas fuera del comando.

## Estilo

- Preguntas tipo: “¿Presupuesto tope?” / “¿URL o solo el nombre?” / “¿Para cuándo?”
- Tras guardar: confirmación corta (como capture). Sin “si quieres te armo un plan”.
