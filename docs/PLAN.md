# Kore — Plan vivo

> Cursor: lee este archivo al empezar trabajo de producto/arquitectura.
> Si cambia una decisión, fase, alcance o se completa un ítem → actualiza este documento en el mismo cambio.

| Campo | Valor |
|-------|--------|
| Repo | `jonoyanguren/kore` |
| Producto | **Kore** (deploy/código) · hablado **Jone** (`ASSISTANT_NAME`) |
| Arquitectura | Companion kernel (Approach B) |
| Fase actual | **Phase 1.5** hecha (consola chat+board) → **1.6 UX personal** siguiente |
| Canal | Telegram (móvil) + consola web (operar / día) |
| Deploy | Fly.io · volumen `/data` |
| LLM | **OpenRouter** (`OPENROUTER_API_KEY` + `OPENROUTER_MODEL`) |
| Modelo default | `xiaomi/mimo-v2.5` |
| Diseño detallado | `docs/companion-plan.md` |
| Consola web 1.5 | `docs/web-console-plan.md` |
| Backlog tareas | `docs/TODO.md` |
| QA / pruebas | `docs/QA.md` |

## Estado

- [x] Repo GitHub `kore` + remote apuntando ahí
- [x] Nombre proyecto Kore + nombre hablado Jone (editable)
- [x] Phase 0 (parcial): prompts, skills, PromptAssembler, SkillRegistry, CommandRouter
- [x] Phase 0 (parcial): `memory_items` + `diary_entries` + `messages` + migración `notes`
- [x] Phase 0 (parcial): tools `save_memory` / `add_diary_entry` + comandos `/skills` `/hora` `/diario`
- [x] Phase 0: imágenes Telegram → MIMO (download + content multimodal)
- [x] Phase 1 (MVP): vault + dream 9am/`/dream` + tasks/agenda locales
- [x] Phase 1.5: consola web (chat texto + board tareas) — MVP
- [ ] Phase 1.6: UX personal premium (day strip, chat vivo, tareas ricas, voz…)
- [ ] Phase 2: Gmail OAuth + digest 9am
- [ ] Phase 3: misiones background
- [ ] Phase 4: git/código (este repo → multi-repo)
- [ ] Phase 5+: calendar, PDF, media web…

## Decisiones (cerradas)

| # | Decisión | Valor |
|---|----------|--------|
| D1 | Arquitectura | Companion kernel |
| D2 | Gmail | OAuth, refresh en `/data` |
| D3 | Git | Primero este repo; luego `/data/repos/` |
| D4 | Nombre | Kore (código) · Jone (hablado, editable) |
| D5 | Personalidad | Stub ahora; se escribe después |
| D6 | Tareas | Sistema propio (SQLite/vault); ClickUp aparcado |
| D7 | Skills | Markdown en git + frontmatter; comandos = disparo |
| D8 | LLM | **OpenRouter**; modelo MIMO multimodal (`xiaomi/mimo-v2.5`) |
| D9 | Memoria | Captura por **categoría**, no log cronológico plano |
| D10 | Confirmación destructiva | Inline keyboard Telegram (web: botones/confirm después) |
| D11 | Orden | Kernel por fases; rename no bloquea |
| D12 | UI web | Phase **1.5** antes de Gmail: chat **texto** + tareas; sin media en web v1; Telegram sigue |
| D13 | Frontend | **Vite + React + TypeScript** desde el inicio (voz/transcripción = slices posteriores, misma SPA) |
| D14 | UX 1.6 | Super-herramienta **personal** con barra UX alta; multi-user/venta = más adelante, fuera de 1.6 |

## Roadmap

### Phase 0 — Kernel + captura *(hecho)*

Hecho:
- `prompts/system.md`, `prompts/personality.md` (stub)
- Skills: `time-madrid`, `capture`, `brainstorm`, `plan`, `execute`
- `app/kernel/`: PromptAssembler + SkillRegistry + CommandRouter
- Comandos: `/skills`, `/hora`, `/diario` (+ skills con `/captura`, `/brainstorm`, …)
- Historial sesión del día (Europe/Madrid) en `messages`
- Tools: `save_memory`, `add_diary_entry`, `forget_memory` (+ aliases legacy)
- Migración `notes` → `memory_items` category=`general`
- Dockerfile copia `prompts/` + `skills/` + `docs/`
- Default model MIMO
- Contexto proyecto (PLAN/TODO/skills/prompts) cada turno

### Phase 1 — Diario / agenda / sueño *(MVP en curso)*

Hecho:
- Vault bajo `VAULT_ROOT` / sibling de DB: `memory/`, `diary/`, `agenda/`, `dreams/` (write-through + rewrite en dream)
- Tablas `tasks`, `agenda_items`, `jobs`
- Tools: `add_task`, `list_tasks`, `get_task`, `update_task`, `complete_task`, `delete_task`, `add_agenda_item`, `list_agenda`
- Tasks: url + project + status `open|in_progress|done|cancelled`; `/tareas` muestra links/notas; mirror `vault/tasks/open.md`
- Skills `/tareas` `/agenda` `/dream` (+ cron in-process **09:00 Madrid**; HTTP manual opcional)
- Dream lee `messages` del día, rellena huecos con tools, vault + briefing Telegram (resumen + prep)
- Prompt: open tasks + agenda upcoming

Pendiente Phase 1:
- Dogfood dream/tasks unos días
- (opcional) fusionar duplicados de memoria más agresivo; briefing aún más rico

### Phase 1.5 — Consola web *(MVP hecho)*

> Diseño: [`docs/web-console-plan.md`](./web-console-plan.md)

Hecho: auth `CONSOLE_SECRET`, Vite+React board (DnD) + chat texto (`/api/chat`), Docker multi-stage, Fly.

### Phase 1.6 — UX personal premium *(siguiente)*

Objetivo: **super-herramienta para Jon** con UX/UI de producto caro. No multi-usuario ni venta ahora; la barra alta es para que la herramienta no se sienta “admin interno”.

Fuera de alcance 1.6: otros usuarios, onboarding comercial, billing, colab, OAuth multi-tenant.

Alcance (orden de ataque):

1. **Day strip** — fecha Madrid + briefing/dream + próximas agenda arriba de chat/board
2. **Chat vivo** — status en vivo (SSE) + acciones Abrir / En curso / Hecha ✅
   *(token streaming del LLM aplazado; el valor es status de tools + acciones)*
3. **Tarjeta de tarea rica** — editar inline (proyecto, url, notas, due); filtros por proyecto; buscar
4. **Voz one-tap** — mic → transcripción → enviar (misma SPA)
5. **⌘K / command palette** — dream, hora, nueva tarea, saltar a proyecto ✅
6. **Layouts** — Focus (chat) / Operate (board) / Day (briefing+agenda) ✅ look Momentum
7. **Drawer memoria/diario** — por categoría + meter en diario ✅
8. **Feedback de sistema** — guardado, error LLM recuperable, tip “sync con Telegram”
9. **Design system** — tokens, empty states, mobile pulido (marca propia, no genérico AI)
10. **Proyectos como espacios** — color + contexto (Kimay / Kore / personal…)
11. **Privacidad personal** — export vault, ver qué sabe, borrar categoría
12. **Inbox del día** — cuando exista Gmail (Phase 2): cola unificada mail + tareas + capturas

### Phase 2 — Gmail

- OAuth + triage + digest 09:00 + `/inbox`
- Hechos del mail → memoria / agenda
- UI: alimentar **Inbox del día** (1.6.12)

### Phase 3 — Misiones

- Cola asyncio, concurrency=1, checkpoints SQLite
- Pipeline brainstorm → plan → execute

### Phase 4 — Código / git

- Este repo primero; confirmación en acciones peligrosas
- Luego multi-repo + skill `self-update`

### Phase 5+

- Calendar externo, PDF, media en web si hace falta

## Success criteria

- [x] System + skills + `/hora` + personalidad stub
- [ ] Chat → hechos guardados por categoría sin pedirlo siempre *(tools listos; falta validar en uso real)*
- [x] `/diario` usable (lectura del día)
- [x] Agenda / tasks locales usables (MVP)
- [x] Imagen Telegram vía MIMO
- [x] Dream 9am consolida chat + memoria (tools + briefing)
- [x] Consola web MVP: chat texto + board tareas (DnD)
- [ ] Day strip + chat con feedback “pensando/tools”
- [ ] Tarea editable inline + filtro por proyecto
- [ ] Voz one-tap en consola
- [ ] Gmail OAuth + digest 9am
- [ ] Una misión background completada
- [ ] Git en este repo con confirmación
- [x] Nombre Kore + Jone editable
- [x] Repo/Fly renombrados a kore

## Open questions

1. Tras Phase 1.6 (o en paralelo): ¿prioridad Gmail o Misiones? — *aplazado*
2. Auth web: sigue `CONSOLE_SECRET` (1 usuario); sin Telegram Login por ahora

## Next steps

1. Dogfood consola + Telegram; verificar briefing ~09:00
2. **Phase 1.6**: Day strip + chat vivo + task cards ricas (antes de Gmail salvo que digas lo contrario)
3. En Cursor: `open` / `close` (`docs/closes/`)
## Changelog del plan

| Fecha | Cambio |
|-------|--------|
| 2026-07-26 | Plan vivo creado desde `companion-plan.md`; fase actual = Phase 0 |
| 2026-07-26 | Phase 0 kernel aterrizado (prompts/skills/assembler/memory/diary/session); pendiente fotos MIMO |
| 2026-07-26 | Añadido `docs/TODO.md` para backlog (primera tarea: mejorar prompts/skills) |
| 2026-07-26 | Fotos Telegram → MIMO cableadas (`download_file` + multimodal content) |
| 2026-07-26 | Prompts/skills reescritos (system, personality, capture/brainstorm/plan/execute/time) |
| 2026-07-26 | Personality de Jon + stub `prompts/kimay.md` ensamblado en el system prompt |
| 2026-07-26 | Tool `get_madrid_time` + skill time-madrid (reloj autoritativo Europe/Madrid) |
| 2026-07-26 | Fijado LLM = OpenRouter (rule + PLAN) |
| 2026-07-26 | Modelo activo `xiaomi/mimo-v2.5` (omni deprecado); secret Fly actualizado |
| 2026-07-26 | Fechas: /hora ES legible; resolve_madrid_date; hablar natural vs guardar ISO |
| 2026-07-26 | Anti-upsell en capture/personality; sesión pausada en dogfood Phase 0 |
| 2026-07-26 | QA repetible: `docs/QA.md`, `tests/`, `scripts/qa_local.sh` |
| 2026-07-26 | Bot lee docs como Cursor: inject PLAN/TODO/agent-rules + tools read_project_doc; COPY docs/ en Docker |
| 2026-07-26 | Skills playbooks completos cada turno + whitelist dinámica prompts/*.md y skills/*.md |
| 2026-07-26 | Convención ship: commit → push → deploy (living-plan) |
| 2026-07-26 | Phase 1 MVP: vault + tasks/agenda + dream cron/`/dream` |
| 2026-07-26 | Gate ship: QA local (uvicorn + pytest + qa_local) antes de commit/push/deploy |
| 2026-07-27 | Dream: cron in-process 09:00 Madrid (GH Actions solo manual) |
| 2026-07-26 | Dream a tope 09:00 Madrid: chat del día + tools + prep |
| 2026-07-26 | Skills split: companion/ (bot) vs dev/ (Cursor); close = dev |
| 2026-07-26 | Closes de desarrollo persistidos en `docs/closes/YYYY-MM-DD.md` |
| 2026-07-26 | Skill `dev/open` para arrancar sesión (último close + PLAN) |
| 2026-07-26 | Regla `dev-session`: auto-open en chat nuevo o frío |
| 2026-07-27 | Tasks: url/project/status + listado con links; delete/update/get tools |
| 2026-07-27 | `/tareas`: secciones En curso → Pendientes; sin footer SQLite |
| 2026-07-27 | Phase **1.5** consola web (chat texto básico + tareas) antes de Gmail; D12 |
| 2026-07-27 | Plan implementación consola: `docs/web-console-plan.md` (slices A–D) |
| 2026-07-27 | D13: frontend Vite+React+TS desde el inicio; voz = post-v1 |
| 2026-07-27 | Phase 1.5 slice A: `/api` auth+tasks + scaffold `web/` |
| 2026-07-27 | Phase 1.5 slice C: `/api/chat` + `/api/messages` + panel chat en consola |
| 2026-07-27 | Phase **1.6** UX personal premium (day strip, chat vivo, tareas, voz…); sin multi-user |
