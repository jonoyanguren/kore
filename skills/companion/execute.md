---
name: execute
description: Avanzar el siguiente paso concreto de un plan o petición, usando tools si hace falta.
commands: [/execute]
tools: [save_memory, add_diary_entry]
---

# Execute

Mode: ship the next step — not the whole roadmap in one breath.

## Loop
1. Identify the immediate next step from the recent plan or the user's ask.
2. Do it: use tools when real data or persistence is required.
3. Report: what you did, result, what remains (1–3 lines).
4. Capture: if the step changed durable status, save_memory; if it happened today, add_diary_entry.

## Guardrails
- Destructive / irreversible / external side effects → stop and ask for explicit yes in chat first.
- If blocked, say the blocker and the smallest unblock action — do not silently invent progress.
- Prefer one solid step per turn unless they ask to continue.
- Never burn the whole turn on tools with no written answer — tools then text summary every turn.

## Exit
Offer the next step: "¿Seguimos con el siguiente?"
