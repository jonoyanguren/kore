# Kore — Plan vivo

> Cursor: lee este archivo al empezar trabajo de producto/arquitectura.
> Si cambia una decisión, fase, alcance o se completa un ítem → actualiza este documento en el mismo cambio.

| Campo | Valor |
|-------|--------|
| Repo | `jonoyanguren/kore` |
| Producto | **Kore** (deploy/código) · hablado **Jone** (`ASSISTANT_NAME`) |
| Arquitectura | Companion kernel (Approach B) |
| Fase actual | **Phase 1** (vault + dream + tasks locales) |
| Canal | Telegram (UI web después) |
| Deploy | Fly.io · volumen `/data` |
| LLM | **OpenRouter** (`OPENROUTER_API_KEY` + `OPENROUTER_MODEL`) |
| Modelo default | `xiaomi/mimo-v2.5` |
| Diseño detallado | `docs/companion-plan.md` |
| Backlog tareas | `docs/TODO.md` |
| QA / pruebas | `docs/QA.md` |

## Estado

- [x] Repo GitHub `kore` + remote apuntando ahí
- [x] Nombre proyecto Kore + nombre hablado Jone (editable)
- [x] Phase 0 (parcial): prompts, skills, PromptAssembler, SkillRegistry, CommandRouter
- [x] Phase 0 (parcial): `memory_items` + `diary_entries` + `messages` + migración `notes`
- [x] Phase 0 (parcial): tools `save_memory` / `add_diary_entry` + comandos `/skills` `/hora` `/diario`
- [x] Phase 0: imágenes Telegram → MIMO (download + content multimodal)
- [x] Phase 1 (MVP): vault + dream 3am/`/dream` + tasks/agenda locales
- [ ] Phase 2: Gmail OAuth + digest 9am
- [ ] Phase 3: misiones background
- [ ] Phase 4: git/código (este repo → multi-repo)
- [ ] Phase 5+: calendar, voz, UI, PDF

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
| D10 | Confirmación destructiva | Inline keyboard Telegram |
| D11 | Orden | Kernel por fases; rename no bloquea |

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
- Tools: `add_task`, `list_tasks`, `complete_task`, `add_agenda_item`, `list_agenda`
- Skills `/tareas` `/agenda` `/dream` (+ cron 03:00 Europe/Madrid)
- Prompt: open tasks + agenda upcoming

Pendiente Phase 1:
- Briefing matutino opcional
- Dogfood dream/tasks unos días
- (opcional) fusionar duplicados de memoria de forma más agresiva en dream

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

- Calendar externo, voz, UI web, PDF

## Success criteria

- [x] System + skills + `/hora` + personalidad stub
- [ ] Chat → hechos guardados por categoría sin pedirlo siempre *(tools listos; falta validar en uso real)*
- [x] `/diario` usable (lectura del día)
- [x] Agenda / tasks locales usables (MVP)
- [x] Imagen Telegram vía MIMO
- [x] Dream 3am consolida memoria (MVP + `/dream`)
- [ ] Gmail OAuth + digest 9am
- [ ] Una misión background completada
- [ ] Git en este repo con confirmación
- [x] Nombre Kore + Jone editable
- [x] Repo/Fly renombrados a kore

## Open questions

1. Tras Phase 0–1: ¿prioridad Gmail o Misiones? — *aplazado*

## Next steps

1. Dogfood Phase 1: `/tareas` `/agenda` `/dream` unos días
2. Briefing matutino opcional o pasar a **Phase 2** (Gmail) según prioridad
3. **Ship siempre:** uvicorn local + pytest + `qa_local.sh` → commit → push → deploy

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
