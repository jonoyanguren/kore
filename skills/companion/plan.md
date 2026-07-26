---
name: plan
description: Convertir contexto o brainstorm en un plan accionable por pasos (sin ejecutar aún).
commands: [/plan]
tools: [save_memory, add_diary_entry]
---

# Plan

Mode: converge. Turn the current topic into something they can execute.

## Output shape (plain text)
1. Objetivo — one sentence
2. Pasos — numbered, each doable in one sitting when possible
3. Riesgos / dependencias — only if real
4. Siguiente acción — the single next move

## Rules
- Prefer fewer sharp steps over a bloated roadmap.
- Use Europe/Madrid if the plan involves days/times.
- Do NOT execute tools that change external systems unless they explicitly ask to start.
- Offer to save: save_memory(projects or work) for the decided approach; add_diary_entry if they commit to doing something today.
- If context is too thin, ask one clarifying question before planning.

## Exit
Ask whether to /execute the first step or adjust the plan.
