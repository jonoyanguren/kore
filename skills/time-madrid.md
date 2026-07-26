---
name: time-madrid
description: Fecha/hora reales en Europe/Madrid vía tool get_madrid_time (nunca inventar el reloj).
commands: [/hora]
tools: [get_madrid_time]
---

# Time Madrid

Canonical timezone: **Europe/Madrid**.

## Mandatory tool
Before answering anything that depends on "now", "today", "mañana", "el viernes",
deadlines, diary day, or "qué hora es", call **get_madrid_time**.
Do not trust memory, training cutoff, or a stale "Now" line alone when precision matters —
the tool is the source of truth.

## /hora
Answer only with the Madrid date and time from get_madrid_time (human field), no lecture.

## Rules
- Never assume UTC or the server's local zone.
- Resolve relative phrases (mañana, esta noche, el lunes) against the tool result.
- Diary "hoy" = the `date` field from get_madrid_time.
