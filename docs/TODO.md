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

- [ ] Meter comandos por voz
- [x] Estados en tareas (`open` / `in_progress` / `done` / `cancelled`) + proyecto + links
- [ ] Que las tareas se autorrellenen más en chat (seguir dogfood)
- [x] Links/notas visibles en `/tareas` (2026-07-27)
- [ ] Hacer la UI
- [ ] Mensajes de 'pensando' o 'esto llevará un ratillo'
- [ ] Meter contexto de proyectos que estoy haciendo (lol, kimay, ...)
- [ ] Conexión con Gmail

## Notas

- Kimay merece su propio prompt (ya cableado en PromptAssembler). No meter todo en personality.
