---
name: close
description: Cierre de sesión de desarrollo en Cursor — qué quedó hecho, dónde lo dejamos, cómo seguir.
scope: dev
---

# Close (desarrollo Kore)

Usar cuando Jon diga que cierra, "resumen de hoy", "dónde lo dejamos", o pida aparcar la sesión de **desarrollo** (Cursor), no el cierre de vida personal de Telegram.

No confundir con `skills/companion/dream.md` (briefing matutino del companion).

## Objetivo

Dejar el hilo listo para la siguiente sesión de código: hechos, punto de retoma, siguientes pasos en docs.

## How (obligatorio)

1. Mira el trabajo de la sesión (diff, commits recientes, conversación).
2. Actualiza en el **mismo cambio** si aplica:
   - `docs/TODO.md` — marca hechos / añade pendientes concretos
   - `docs/PLAN.md` — next steps + changelog breve si cambió fase/alcance
3. Responde en texto plano (o markdown ligero en Cursor), estructura fija:

A) Hecho hoy — bullets concretos (PRs, features, deploys)  
B) Dónde lo dejamos — archivo/módulo/decisión a medias; el siguiente click mental  
C) Para seguir — 2–5 pasos accionables (idealmente ya en TODO)  
D) Una frase de cierre  

4. No hagas commit/push/deploy salvo que Jon lo pida.
5. Si hay cambios locales sin commitear, menciónalo en B.

## Dual use (más adelante)

Esta skill es **dev** (Cursor). Si algún día se quiere el mismo ritual en Telegram sobre el chat del día, crear o enlazar una companion skill / runner aparte — no mezclar scopes en silencio.
