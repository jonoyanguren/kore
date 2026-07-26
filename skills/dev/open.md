---
name: open
description: Arranque de sesión de desarrollo — lee último close + PLAN y propone foco como PM senior.
scope: dev
---

# Open (desarrollo Kore)

Usar cuando Jon diga "open", "arrancamos", "dónde estábamos", "qué toca hoy", o empiece sesión de **desarrollo** en Cursor.

También: la regla `.cursor/rules/dev-session.mdc` exige **auto-open** en chat nuevo o hilo frío (de hace tiempo) — no esperes a que lo pida.

No confundir con skills companion de Telegram ni con el dream de las 9am.

## Objetivo

Entrar en contexto en &lt;2 minutos: estado real, foco del día, riesgos, y 2–3 caminos posibles — tono **project manager senior** que ya conoce el producto (no kickoff genérico).

## Lectura obligatoria (en este orden)

1. **Último close:** el `docs/closes/YYYY-MM-DD.md` más reciente (por nombre de fecha). Si hay close de hoy, úsalo.
2. `docs/PLAN.md` — Fase actual, Next steps, Success criteria abiertos, Changelog reciente.
3. `docs/TODO.md` — ítems abiertos relevantes (no regurgites todo el backlog).
4. Si hace falta detalle de diseño: `docs/companion-plan.md` (solo el trozo de la fase).
5. `git status` / commits recientes si hay trabajo local sucio o duda de ship.

Sin haber leído (1)+(2) no inventes el estado.

## Output (mensaje a Jon) — estructura fija

Texto claro (markdown ligero OK en Cursor):

### 1) Dónde estamos
3–6 líneas: fase, último close en una frase, si hay cambios locales sin ship.

### 2) Foco recomendado hoy
**Una** apuesta principal (el siguiente paso de más apalancamiento). Por qué esa y no otra. Criterio de “hecho” para hoy (testable).

### 3) Plan del día (90 min / half-day)
Checklist corto ordenado (3–6 pasos). Incluye QA/ship si el trabajo toca bot.

### 4) Alternativas / brainstorm
2–3 opciones de camino (A/B/C) con trade-off en una línea cada una. Elige una como default; las otras quedan aparcadas.

### 5) Riesgos y deudas
Solo lo que puede joder esta semana (secrets, dogfood pendiente, scope creep…).

### 6) Pregunta de arranque
Una sola pregunta si falta una decisión de Jon; si no falta, di “puedo empezar por X” y espera OK o corrección.

## Tono

- Directo, prioriza, corta ruido.
- Habla como quien lleva el proyecto: “hoy cerramos X; Y puede esperar”.
- No elevator pitch. No “si quieres te armo un plan” — **el plan ya va en el mensaje**.
- No implementes código en el open salvo que Jon diga “dale” / “implementa”.

## Persistencia (opcional)

Si Jon pide “deja el open escrito” o el arranque es gordo, escribe:

`docs/opens/YYYY-MM-DD.md`

con el mismo contenido del mensaje. Por defecto **no** hace falta (el close de ayer + este mensaje bastan).

## Relación con close

| Skill | Cuándo | Artefacto |
|-------|--------|-----------|
| `open` | Arrancar | Lee `docs/closes/*` + PLAN |
| `close` | Cerrar | Escribe `docs/closes/YYYY-MM-DD.md` |

## No hacer

- Empezar a codear sin foco acordado.
- Repetir todo el PLAN.md.
- Tratar open como dream de Telegram.
