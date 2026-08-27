# Kore — Plan vivo

> Cursor: lee esto al empezar producto/arquitectura. Actualízalo si cambia fase o decisión.
> Histórico de hitos: [`milestones.md`](./milestones.md) · Backlog abierto: [`TODO.md`](./TODO.md)

| Campo | Valor |
|-------|--------|
| Repo | `jonoyanguren/kore` |
| Producto | **Kore** · hablado **Jone** (`ASSISTANT_NAME`) |
| Fase actual | **UI landing → consola** — mismo sistema visual; 1.6 layout cuando llegue diseño |
| Canal | Consola web = operar / día · Telegram = captura móvil opcional |
| Deploy | Fly.io · `/data` |
| LLM | OpenRouter · diario `deepseek/deepseek-v4-pro` · strong `claude-haiku-4.5` · misiones Normal=`deepseek-v4-flash` / Loco·Experto·Duro=`deepseek-v4-pro` · prompt cache en tool loops |
| Diseño largo | `companion-plan.md` · Consola 1.5: `web-console-plan.md` |
| Backlog | `TODO.md` · **Producto** vs **Plataforma** |

## Estado

- [x] Phase 0 — Kernel + captura
- [x] Phase 1 — Vault / tasks / dream (cron 09:00 Madrid in-process)
- [x] Phase 1.5 — Consola web MVP (chat + board)
- [ ] Phase 1.6 — UX personal *(parcial: chrome visual = landing 2026-08-27; layout cuando llegue diseño)*
- [x] Phase 2 — Gmail MVP
- [x] Phase 3 — Misiones *(MVP + dogfood + UI Resultado)*
- [ ] ~~Phase 4 — Git / código~~ → **fuera de Kore** (proyecto aparte: programar desde el móvil)
- [x] Agenda + Google Calendar *(read + write bloque; D24/D25 cerrado 2026-08-27)*
- [ ] Phase 5+ — PDF, media… *(candidatos)*
- [ ] App móvil Kore — día a día (Expo; no es el IDE móvil)

## Decisiones (cerradas)

| # | Valor |
|---|--------|
| D1 | Companion kernel |
| D2 | Gmail OAuth (`gmail.modify` + send reply) → `/data` |
| D3 | **Git/código fuera de Kore** — sistema de programar desde móvil = repo/producto aparte (2026-08-10). Antes: “este repo primero” — **superseded** |
| D4 | Kore (código) · Jone (hablado) |
| D6 | Tasks propias (SQLite/vault); ClickUp aparcado |
| D7 | Skills markdown + frontmatter |
| D8 | OpenRouter + MIMO multimodal |
| D9 | Memoria por categoría |
| D12 | UI web 1.5 antes de Gmail |
| D13 | Vite + React + TS |
| D14 | **Cuentas aisladas** (2026-08-26): registro abierto email+password, **sin invitaciones**. Cada usuario = home propio (`/data/users/{id}/kore.db` + `vault/` + Gmail tokens). `accounts.db` solo usuarios/sesiones. Telegram sigue siendo Jon (`telegram_allowed_chat_id`). Prompts Kimay/Slow/investing/PLAN solo si `legacy_prompts`. MVP original “no multi-user” → **superseded**. |
| D15 | Briefing matutino → **vista Día**; Telegram notify off por defecto |
| D16 | Gmail MVP = OAuth + Día/`/inbox` + dream Inbox + triage log |
| D17 | Gmail send = **reply/answer**: borrador editable → confirmar (`gmail.send`; no compose frío en v1) |
| D18 | Misión = input → loop → output; no bloquea chat; resultado markdown en vault |
| D19 | Misiones UI: **4º layout**; lista + «Ocultar terminadas»; **Nueva** inicia el input |
| D20 | Persistencia: **SQLite** lista/estado · **vault** `missions/{id}.md` = output |
| D21 | Loop: ticks (`next_run_at`); runner in-process; max 1 activa v1 |
| D22 | Misiones: **plan → N tareas**; handoff corto; summary pass → `## Resultado` |
| D23 | Dogfood Phase 0–3 **cerrado** (2026-08-10); siguiente = features nuevas, no más “vivir el MVP” |
| D24 | **Google Calendar read-only** vía mismo OAuth (`calendar.readonly`); solo calendario **primary** (no suscripciones); eventos live en Día + dream + tool chat; **no** duplicar a SQLite en v1; agenda local sigue para captura chat |
| D25 | **Chat → crear bloque Calendar**: tool `create_calendar_block` escribe ya en primary; pregunta solo si hay duda real |
| D27 | **Misiones intake** (2026-08-27): aclarar pide 5–8 preguntas (no 1–2); ronda 2 = huecos; ready solo con brief usable |
| D28 | **Misiones leen memoria** (2026-08-27): digest + `list_memory` (solo lectura). No vuelcan el vault. Web sigue siendo la herramienta principal |

## Roadmap (lean)

**Cerrado Phase 3:** misiones usable + dogfood + UI Resultado.

**Cerrado Calendar (D24/D25):** read primary + crear bloque desde chat. Dogfood aparcado; no más slice ahora.

**Ahora — misiones:** intake largo (5–8 preguntas) + UI al lenguaje landing. Allowlist aparcado.

**1.6 / layout:** rediseño externo de estructura → maquetar cuando llegue (el chrome ya no espera).

**App móvil Kore:** captura / Día / audio — **no** sustituye el proyecto de programar desde el móvil.

Detalle shipped → [`milestones.md`](./milestones.md).

## Success (vivo)

- [x] Kernel, tasks, dream 09:00, consola MVP
- [x] Day strip + chat vivo + tareas ricas + layouts + memoria drawer
- [x] Voz · privacidad · gasto LLM · proyecto inferido
- [x] Dogfood consola + Gmail + Misiones
- [x] Phase 3 Misiones usable
- [x] Google Calendar read en Día / dream / chat (D24)
- [x] Chat → crear bloque Calendar (D25) — cerrado 2026-08-27 (dogfood aparcado)
- [x] Landing pública (logged-out) — hero + Día/Companion/Misiones; Entrar / Crear cuenta
- [x] Consola visual = landing (canvas / papel / tipo / píldoras) — 2026-08-27
- [ ] Rediseño UI layout (diseño externo → maquetar)
- [ ] App móvil día a día (Kore)

## Next steps

1. Dogfood intake de una misión vaga → 5–8 Qs → brief
2. Pulir Board si queda corto vs landing
3. Allowlist / rate-limit registro si hay spam

No hinchar este archivo: cerrar → `milestones.md` + TODO corto.

## Changelog (reciente)

| Fecha | Cambio |
|-------|--------|
| 2026-08-27 | **D28** Misiones: digest de memoria + tool `list_memory` (lectura). No el vault entero |
| 2026-08-27 | Consola beige a pantalla completa (sin canvas negro); mismo ancho 52rem |
| 2026-08-27 | Consola: mismo ancho de página (52rem) en Día, Chat, Board y Misiones |
| 2026-08-27 | **D27 Misiones intake:** 5–8 preguntas ronda 1; follow-up ronda 2; UI Nueva al estilo landing |
| 2026-08-27 | **UI consola = landing:** canvas `#12151a`, papel `#f3efe8`, Instrument Sans, botones píldora |
| 2026-08-27 | **Landing pública:** logged-out = hero tipo Revolut (claim + producto); overlay Entrar/Crear cuenta; cookie skip a consola |
| 2026-08-27 | **D25 cerrado:** Calendar write marcado hecho (dogfood aparcado); siguiente = landing |
| 2026-08-26 | **D14 superseded:** registro abierto; homes SQLite aislados; onboarding nombre+tono; Telegram = Jon |
| 2026-08-26 | **D26** Misiones: modos Normal / Loco / Experto / Duro + leyenda en Nueva (sustituye Calidad) |
| 2026-08-10 | **Dream fiable:** `/dream` consola; retry modelo; fallback determinista; Día con help vivo |
| 2026-08-10 | Calendar Día: acciones **Abrir / Tarea / Prep**; spike write desde chat (`docs/spikes/calendar-write.md`) |
| 2026-08-10 | **D24 shipped (code):** Calendar read — primary only; Día/dream/tool |
| 2026-08-10 | **D24** siguiente = Google Calendar read (mismo OAuth Gmail); Git sigue fuera |
| 2026-08-10 | Dogfood cerrado; Phase 3 done; **D3 supersede**: Git/código → proyecto aparte |
| 2026-08-10 | Misiones UI: Resultado con bloques de color + tablas tipo card |
| 2026-08-10 | Misiones: summary pass + Resultado card + 1 accordion investigación |
| 2026-08-09 | Tareas: Copiar URL; skill `/entrevista` + `list_memory` |
| 2026-07-30 | Móvil M0 Expo; TODO Producto vs Plataforma; PWA atajo |
| 2026-07-30 | Misiones Normal/Pro + imágenes md |
| 2026-07-29 | Ledger LLM; D22 plan→tareas; aclaración Nueva |
| 2026-07-28 | Phase 2 Gmail + D17 reply; Phase 3 esqueleto→loop real |
| 2026-07-27 | Consola 1.5/1.6 parcial; dream 09:00; milestones split |

Histórico largo → `milestones.md`.
