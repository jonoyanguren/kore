---
name: close
description: Cierre de sesión de desarrollo en Cursor — qué quedó hecho, dónde lo dejamos, cómo seguir.
scope: dev
---

# Close (desarrollo Kore)

Usar cuando Jon diga que cierra, "resumen de hoy", "dónde lo dejamos", o pida aparcar la sesión de **desarrollo** (Cursor), no el cierre de vida personal de Telegram.

No confundir con `skills/companion/dream.md` (briefing matutino del companion).

## Objetivo

Dejar el hilo listo para la siguiente sesión de código: hechos, punto de retoma, siguientes pasos en docs — **y un archivo legible mañana**.

## Persistencia (obligatorio)

Escribe o sobrescribe:

`docs/closes/YYYY-MM-DD.md`

(fecha = día Europe/Madrid de la sesión). Sin ese archivo el close está incompleto.

Opcional: si ya existe un close del mismo día, **actualízalo** (no borres historia útil; fusiona).

## How (obligatorio)

1. Mira el trabajo de la sesión (diff, commits recientes, conversación).
2. Actualiza en el **mismo cambio** si aplica:
   - `docs/TODO.md` — marca hechos / añade pendientes concretos
   - `docs/PLAN.md` — next steps + changelog breve si cambió fase/alcance
3. **Escribe** `docs/closes/YYYY-MM-DD.md` con la estructura A–D (abajo).
4. Responde a Jon con el mismo A–D (puede ser el contenido del archivo).
5. Si Jon pide commit/push, incluye el archivo de close en el commit.

### Estructura del archivo y del mensaje

```markdown
# Close — YYYY-MM-DD (desarrollo Kore)

## A) Hecho hoy
- …

## B) Dónde lo dejamos
- …

## C) Para seguir
1. …
2. …

## D) Cierre
…
```

A) Hecho hoy — bullets concretos (PRs, features, deploys)  
B) Dónde lo dejamos — archivo/módulo/decisión a medias; el siguiente click mental  
C) Para seguir — 2–5 pasos accionables (idealmente ya en TODO)  
D) Una frase de cierre  

## Arranque mañana

Al empezar sesión de desarrollo: lee el **último** `docs/closes/*.md` (o el de hoy si existe) + `docs/PLAN.md` Next steps.

## No hacer

- Close solo en el chat sin escribir `docs/closes/`.
- Commit/push/deploy salvo que Jon lo pida.
- Confundir con dream de Telegram.

## Dual use (más adelante)

Esta skill es **dev** (Cursor). Un cierre de vida en Telegram sería companion skill / runner aparte.
