# Kore — TODO

Backlog de tareas sueltas. El plan vivo (`docs/PLAN.md`) marca fase/alcance; aquí van cosas concretas para no olvidar.

Convención: `- [ ]` pendiente · `- [x]` hecho. Añade fecha o contexto breve si ayuda.

## Prompting & skills

- [x] Mejorar los prompts y skills — baseline sólido en `prompts/` + `skills/` (2026-07-26)
- [x] Personalizar `prompts/personality.md` con voz de Jon (tuteo, directo, humor chorra, plan-first)
- [x] Rellenar `prompts/kimay.md` — baseline (software, full stack, emprendedor/inversor, datafineai; farma = no inventar)
- [x] Ampliar Datafine desde web pública (hiperpersonalización ecommerce)
- [x] Prompt `slow-project.md` — Citrus Designer + YaY Experiences + HomePrive (Slow Project SL)
- [x] Prompt `investing.md` — faceta inversor (azValor: ~60k + 18k aportados → ~107k actual)
- [ ] Ampliar investing más adelante si quiere (horizonte, otras gestoras, recordatorios)
- [ ] Confirmar rol de Jon en Slow Project / relación con Andrea
- [ ] Confirmar/corregir Datafine + About si hace falta
- [ ] Decidir agresividad de captura (proactiva vs solo con “recuerda/captura”)
- [ ] Meter varios modelos, uno para imagenes, otro para code...



## Kernel / producto

- [x] Cablear imágenes Telegram → MIMO (Phase 0)
- [x] Skill/tool hora Madrid bien (`get_madrid_time` + skill time-madrid)
- [x] Fechas: /hora legible ES; guardar ISO; hablar natural (`resolve_madrid_date`)
- [x] Plan de pruebas repetible: `docs/QA.md` + `pytest` + `scripts/qa_local.sh`
- [x] Jone lee contexto de proyecto (PLAN/TODO/agent-rules inyectados + `read_project_doc`)
- [x] Skills/prompts completos cada turno + whitelist dinámica
- [x] Convención documentada: commit → push → deploy
- [x] Phase 1 MVP: vault + tasks/agenda + dream 3am/`/dream`
- [x] Sueño vía **cron externo** (no polling): `POST /internal/cron/dream` + GitHub Actions ~**09:00 Madrid**
- [x] Dream a tope: transcript del día + tools (huecos) + resumen Telegram + prep día siguiente
- [x] Separar `skills/companion/` (Telegram) vs `skills/dev/` (Cursor); `dev/close` → `docs/closes/YYYY-MM-DD.md`
- [x] Skill `dev/open` — arranque leyendo último close + PLAN (PM senior)
- [x] Regla Cursor `dev-session`: auto-open en chat nuevo o frío
- [x] `CRON_SECRET` en Fly (GitHub repo secret: confirmar si ya lo metiste)
- [ ] Verificar una vez el briefing de las 09:00 en Telegram
- [ ] Dogfood dream/tasks en Telegram unos días
- [x] Gate ship: QA local (uvicorn + pytest + qa_local) antes de commit/push/deploy



## Tareas

- [x] Estados en tareas (`open` / `in_progress` / `done` / `cancelled`) + proyecto + links
- [x] Links/notas visibles en `/tareas` (2026-07-27)
- [x] `/tareas` agrupado En curso → Pendientes, sin pie SQLite (2026-07-27)
- [ ] Que las tareas se autorrellenen más en chat (seguir dogfood)
- [ ] Mensajes de 'pensando'… → Phase 1.6 chat vivo
- [ ] Contexto proyectos (lol, kimay, …) → Phase 1.6 espacios
- [ ] Voz → Phase 1.6 voz one-tap
- [ ] Gmail → Phase 2 (después de 1.6 salvo que digas lo contrario)



## Consola web (Phase 1.5) — MVP

Plan: [`docs/web-console-plan.md`](./web-console-plan.md)

- [x] **A** Scaffold Vite+React+TS + auth + API tasks + tests (2026-07-27)
- [x] **B** UI React board Trello (DnD En curso / Pendientes / Hechas) (2026-07-27)
- [x] **C** `POST /api/chat` + UI chat texto (2026-07-27)
- [x] **D** Docker multi-stage + `CONSOLE_SECRET` Fly (2026-07-27)
- [x] Servir `web/dist` desde FastAPI

## UX personal premium (Phase 1.6)

Super-herramienta para Jon; barra UX alta. **No** multi-user / venta / billing.

Orden:
1. [x] Day strip (fecha Madrid + briefing/dream + agenda próxima) (2026-07-27)
2. [ ] Chat vivo (“pensando / tools…”, streaming si cabe; acciones en respuesta) — thinking baseline 2026-07-27
3. [ ] Tarjeta tarea editable (proyecto, url, notas, due) + filtros + buscar
4. [ ] Voz one-tap (mic → transcripción → enviar)
5. [ ] ⌘K / command palette (dream, hora, nueva tarea, proyecto)
6. [ ] Layouts Focus / Operate / Day
7. [ ] Drawer memoria/diario (categorías + meter en diario)
8. [ ] Feedback sistema (guardado, error LLM, sync Telegram)
9. [ ] Design system (tokens, empty states, mobile)
10. [ ] Proyectos como espacios (color + contexto Kimay/Kore/…)
11. [ ] Privacidad personal (export vault, qué sabe, borrar categoría)
12. [ ] Inbox del día (cuando Gmail / Phase 2)

## Notas

- Kimay merece su propio prompt (ya cableado en PromptAssembler). No meter todo en personality.

