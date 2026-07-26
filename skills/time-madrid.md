---
name: time-madrid
description: Reloj y fechas relativas (Europe/Madrid). Guarda ISO; en chat habla natural (el lunes que viene, el lunes 24…).
commands: [/hora]
tools: [get_madrid_time, resolve_madrid_date]
---

# Time Madrid

Canonical calendar: Europe/Madrid (no digas "Madrid" ni la zona en el chat salvo que pregunten).

## Tools
- **get_madrid_time** — ahora. Usa `human` para /hora; `date` (YYYY-MM-DD) para guardar "hoy".
- **resolve_madrid_date** — frases relativas ("el lunes que viene", "mañana", "este viernes").
  Devuelve `date` (ISO para almacenar) y `spoken` (cómo decirlo en el chat).

## Guardar vs hablar
- **Almacenar** (memoria, diario, agenda): siempre `YYYY-MM-DD` del tool.
- **Hablar con Jon**: usa `spoken` / formas naturales. Ejemplos:
  - hoy / mañana / ayer
  - el lunes de esta semana
  - el lunes que viene
  - el lunes 24 (si basta el día del mes)
  - solo fecha larga si él la pide o hay ambigüedad de año

No digas "2026-07-28" ni "lunes 28 de julio de 2026" en charla normal.

## /hora
Responde solo con el campo `human` de get_madrid_time (día mes año + hora), sin charla.

## Rules
- Nunca inventes el reloj ni asumas UTC.
- Antes de anclar un "lunes que viene" / "el viernes", llama resolve_madrid_date.
