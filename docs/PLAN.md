# Kore — Plan vivo

> Cursor: lee este archivo al empezar trabajo de producto/arquitectura.
> Si cambia una decisión, fase, alcance o se completa un ítem → actualiza este documento en el mismo cambio.

| Campo | Valor |
|-------|--------|
| Repo | `jonoyanguren/kore` |
| Producto | **Kore** (deploy/código) · hablado **Jone** (`ASSISTANT_NAME`) |
| Arquitectura | Companion kernel (Approach B) |
| Fase actual | **Phase 0 — Kernel + captura** (en dogfood Telegram; prompts/fecha/anti-upsell iterando) |
| Canal | Telegram (UI web después) |
| Deploy | Fly.io · volumen `/data` |
| LLM | **OpenRouter** (`OPENROUTER_API_KEY` + `OPENROUTER_MODEL`) |
| Modelo default | `xiaomi/mimo-v2.5` |
| Diseño detallado | `docs/companion-plan.md` |
| Backlog tareas | `docs/TODO.md` |

## Estado

- [x] Repo GitHub `kore` + remote apuntando ahí
- [x] Nombre proyecto Kore + nombre hablado Jone (editable)
- [x] Phase 0 (parcial): prompts, skills, PromptAssembler, SkillRegistry, CommandRouter
- [x] Phase 0 (parcial): `memory_items` + `diary_entries` + `messages` + migración `notes`
- [x] Phase 0 (parcial): tools `save_memory` / `add_diary_entry` + comandos `/skills` `/hora` `/diario`
- [x] Phase 0: imágenes Telegram → MIMO (download + content multimodal)
- [ ] Phase 1: vault + dream 3am + tasks locales
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

### Phase 0 — Kernel + captura *(en curso)*

Hecho:
- `prompts/system.md`, `prompts/personality.md` (stub)
- Skills: `time-madrid`, `capture`, `brainstorm`, `plan`, `execute`
- `app/kernel/`: PromptAssembler + SkillRegistry + CommandRouter
- Comandos: `/skills`, `/hora`, `/diario` (+ skills con `/captura`, `/brainstorm`, …)
- Historial sesión del día (Europe/Madrid) en `messages`
- Tools: `save_memory`, `add_diary_entry`, `forget_memory` (+ aliases legacy)
- Migración `notes` → `memory_items` category=`general`
- Dockerfile copia `prompts/` + `skills/`
- Default model MIMO

Pendiente Phase 0:
- Seguir dogfood en Telegram (captura, fotos, tono)
- Commit/push de cambios locales post-a5efe0c (MIMO v2.5, fechas, anti-upsell, rules) si aún no están en git
- (opcional) tests unitarios del registry/store

### Phase 1 — Diario / agenda / sueño

- Vault `memory/`, `diary/`, `agenda/`
- Cron 03:00 `dream` + `/dream` manual
- Tasks locales + briefing matutino opcional

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
- [ ] Agenda / tasks locales usables
- [x] Imagen Telegram vía MIMO
- [ ] Dream 3am consolida memoria
- [ ] Gmail OAuth + digest 9am
- [ ] Una misión background completada
- [ ] Git en este repo con confirmación
- [x] Nombre Kore + Jone editable
- [x] Repo/Fly renombrados a kore

## Open questions

1. Tras Phase 0–1: ¿prioridad Gmail o Misiones? — *aplazado*

## Next steps

1. Commit + push de lo desplegado que aún esté dirty en git
2. Seguir probando en Telegram (captura corta, fechas naturales, foto)
3. Cuando Phase 0 se sienta bien → Phase 1 (vault + dream 3am + tasks)

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
