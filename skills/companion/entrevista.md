---
name: entrevista
description: Rellenar huecos del vault (memoria/diario/contexto). Comando = 2–3 Q; chat = max 1 Q.
commands: [/entrevista, /interview]
tools: [list_memory, save_memory, add_diary_entry, forget_memory, list_project_docs, read_project_doc, resolve_madrid_date, get_madrid_time]
---

# Entrevista

Objetivo: **rellenar contexto del vault** (hechos duraderos en memoria, a veces diario). No es triage del board de tareas.

Dos modos. No los mezcles.

## Modo A — comando `/entrevista` (o `/interview`)

### Arranque (obligatorio, primer mensaje)

1. Escanea el **vault / memoria**, no el board:
   - Llama `list_memory` (sin categoría y/o por `people`, `projects`, `work`, `preferences`, `health`, `general`).
   - Usa también digests y diario ya inyectados en el system prompt, y el chat reciente.
   - Opcional: `read_project_doc` (`prompts/kimay.md`, etc.) solo si ayuda a ver qué contexto personal falta frente a un área de vida.
2. Detecta **2–3 huecos de contexto** (datos que, si estuvieran en memoria, te harían útil después). Ejemplos buenos:
   - Persona citada sin rol / relación / cómo contactarla
   - Proyecto o cliente sin qué es / estado / qué importa a Jon
   - Preferencia a medias (herramientas, horarios, “cómo le gusta que le avisen”)
   - Hecho del chat reciente que no está en memoria y le falta un dato
   - Categoría vacía o muy fina frente a algo que Jon usa mucho (Kimay, trabajo, casa…)
3. Responde **ya** con 2–3 preguntas numeradas, cortas, en español. Cada una apunta a un hueco de vault (cita la persona/proyecto/tema, no un id de tarea).
4. **PROHIBIDO:**
   - Preguntar estado de tareas del board (“¿qué queda de la #3?”, “¿ha llegado el correo de…?”, “¿hay plazo de cerrar BI?”).
   - Menú de temas (“¿Kimay, board o algo nuevo?”).
   - Usar `list_tasks` / `update_task` / `add_task` en este modo.
5. Si el vault ya está denso y no ves huecos: di en una línea “No veo huecos claros en memoria” y haz **una** pregunta de contexto útil (gente, preferencias o un proyecto recurrente) — nunca un menú ni triage de tareas.

### Siguientes turns

1. Cuando responda → guarda con `save_memory` (categoría clara) y/o `add_diary_entry` si es evento del día.
2. Confirma en una línea. Si aún faltan datos de la lista, pregunta el siguiente hueco (1 pregunta), o cierra si ya basta.
3. Máximo ~5 preguntas en toda la sesión (las 2–3 del arranque cuentan).
4. **Salidas:** “basta”, “listo”, “para”, “ya está” → resume en 1–3 líneas qué quedó en el vault, STOP.
5. No inventes datos. No lances planes ni misiones. No abras/cierres tareas.

## Modo B — chat normal (sin `/entrevista`)

- Solo pregunta si Jon pide guardar/actuar y falta un dato **sin el cual no se puede**.
- **Máximo una pregunta.** Luego STOP.
- Preferir `capture` STOP si ya se puede apuntar sin más.
- Nunca entrevista espontánea de varias preguntas.

## Estilo

- Bueno: “1) ¿Quién es X en Corpme y qué relación tienes? 2) En Kimay, ¿qué es lo que más te está frenando esta semana? 3) ¿Prefieres que te recuerde cosas por la mañana o al cerrar el día?”
- Malo: “1) Tarea #3 Video Abundio — ¿qué queda? 2) ¿Ha llegado el correo de Corpme?”
- Malo: “¿Sobre qué tema quieres la entrevista?”
- Tras guardar: confirmación corta. Sin “si quieres te armo un plan”.
