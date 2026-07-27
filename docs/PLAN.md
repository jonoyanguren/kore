# Kore — Plan vivo

> Cursor: lee este archivo al empezar trabajo de producto/arquitectura.
> Si cambia una decisión, fase, alcance o se completa un ítem → actualiza este documento en el mismo cambio.

| Campo | Valor |
|-------|--------|
| Repo | `jonoyanguren/kore` |
| Producto | **Kore** (deploy/código) · hablado **Jone** (`ASSISTANT_NAME`) |
| Arquitectura | Companion kernel (Approach B) |
| Fase actual | **Phase 1** (vault + dream + tasks) → **1.5 web** siguiente |
| Canal | Telegram (captura móvil) + **consola web** (chat básico + tareas) |
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
- [ ] Phase 1.5: consola web (chat texto básico + tareas)
- [ ] Phase 2: Gmail OAuth + digest 9am
- [ ] Phase 3: misiones background
- [ ] Phase 4: git/código (este repo → multi-repo)
- [ ] Phase 5+: calendar, voz, PDF, media web…

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
- Skills `/tareas` `/agenda` `/dream` (+ cron externo ~**09:00 Madrid** → `/internal/cron/dream`)
- Dream lee `messages` del día, rellena huecos con tools, vault + briefing Telegram (resumen + prep)
- Prompt: open tasks + agenda upcoming

Pendiente Phase 1:
- Dogfood dream/tasks unos días
- (opcional) fusionar duplicados de memoria más agresivo; briefing aún más rico

### Phase 1.5 — Consola web *(siguiente, acelera dogfood)*

> Diseño de implementación: [`docs/web-console-plan.md`](./web-console-plan.md)

Objetivo: UI propia para operar más rápido que Telegram (listas, checks, botones), sin matar el bot.

Alcance v1:
- Auth mínima (`CONSOLE_SECRET` → cookie/Bearer)
- Frontend **Vite + React + TS** (SPA en `web/dist`)
- **Chat texto** → `LLMAssistant.ask` (voz/transcripción = post-v1, misma app)
- **Tareas**: En curso / Pendientes, completar, editar, links
- Docker multi-stage (node build + python)
- Cortes: A scaffold+API tasks → B UI tareas → C chat → D deploy → E+ voz

Fuera de v1: media, streaming, multi-usuario, agenda/dream UI. Voz prevista en la misma SPA.

### Phase 2 — Gmail

- OAuth + triage + digest 09:00 + `/inbox`
- Hechos del mail → memoria / agenda

### Phase 3 — Misiones

- Cola asyncio, concurrency=1, checkpoints SQLite
- Pipeline brainstorm → plan → execute

### Phase 4 — Código / git

- Este repo primero; confirmación en acciones peligrosas
- Luego multi-repo + skill `self-update`

### Phase 5+

- Calendar externo, voz, PDF, media en web si hace falta

## Success criteria

- [x] System + skills + `/hora` + personalidad stub
- [ ] Chat → hechos guardados por categoría sin pedirlo siempre *(tools listos; falta validar en uso real)*
- [x] `/diario` usable (lectura del día)
- [x] Agenda / tasks locales usables (MVP)
- [x] Imagen Telegram vía MIMO
- [x] Dream 9am consolida chat + memoria (tools + briefing)
- [ ] Consola web: chat texto + completar/editar tarea en <2 clics
- [ ] Gmail OAuth + digest 9am
- [ ] Una misión background completada
- [ ] Git en este repo con confirmación
- [x] Nombre Kore + Jone editable
- [x] Repo/Fly renombrados a kore

## Open questions

1. Tras Phase 1.5: ¿prioridad Gmail o Misiones? — *aplazado*
2. Auth web v1: `CONSOLE_SECRET` + cookie (recomendado en web-console-plan); Telegram Login = no v1

## Next steps

1. Dogfood companion: `/dream`, tareas/agenda; verificar briefing ~09:00
2. **Phase 1.5**: API + chat texto mínimo + panel tareas (antes de Gmail)
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
| 2026-07-26 | Dream: quitar polling 60s; cron HTTP + GitHub Actions |
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
