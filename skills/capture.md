---
name: capture
description: Captura hechos por categoría (memoria) y/o eventos del día (diario) a partir del chat o una foto.
commands: [/captura]
tools: [save_memory, add_diary_entry, forget_memory]
---

# Capture

Goal: turn what the user just said (or showed) into durable memory and/or today's diary — without turning the whole chat into a log.

## When to save
SAVE when it will help future you:
- Status updates ("ya hablé con trabajo", "cerramos el deal")
- People, roles, relationships
- Project decisions, constraints, naming
- Health / habits / preferences that persist
- Clear "remember this" intent

SKIP when:
- Pure brainstorming with no decision
- Throwaway logistics ("llego en 5")
- They say not to store it

## How
1. Split: diary (today's event) vs memory (cross-day fact). Often both.
2. Memory text: one short sentence, present tense, no fluff. Example: "Ya contactó al equipo de trabajo sobre X."
3. Category: work | people | projects | health | preferences | general (or a short custom slug).
4. Call the tools, then confirm in one line: what + where (category / diario).
5. If they only said /captura with no content, ask what to capture — one question.

## Examples
User: "ya he hablado con los del trabajo"
→ add_diary_entry + maybe save_memory(category=work, …)

User: "prefiero que me resumas el mail por la mañana"
→ save_memory(category=preferences, …) only
