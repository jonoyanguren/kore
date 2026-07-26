---
name: project-status
description: Estado del proyecto Kore según PLAN.md / TODO.md (qué toca ahora).
commands: [/estado, /next]
tools: [read_project_doc, list_project_docs]
---

# Project status

Jon pregunta qué toca del **proyecto Kore** (no de su vida personal).

## How
1. Usa el PLAN.md y TODO.md ya inyectados en el system prompt (sección Project file).
2. Si dudas o pide detalle de arquitectura, `read_project_doc` con `docs/companion-plan.md` o `docs/QA.md`.
3. Responde en 2–5 líneas: fase actual + siguiente acción concreta del plan.
4. No inventes commits pendientes ni ofrezcas git si el plan ya dice otra cosa.
5. Sin upsells. Sin presentarte.
