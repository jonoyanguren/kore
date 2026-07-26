---
name: time-madrid
description: Fecha/hora Europe/Madrid; ancla deadlines, diario y "hoy".
commands: [/hora]
tools: []
---

# Time Madrid

Canonical timezone: Europe/Madrid (see "Now" in the system prompt).

## Rules
- Never assume UTC or the server's local zone for "today", diary days, or deadlines.
- /hora → answer with a clear Madrid date and time only (no lecture).
- If the user says "mañana", "el viernes", "esta noche", resolve against the Madrid "Now".
- When writing diary days or interpreting "hoy", use Madrid's calendar date.
