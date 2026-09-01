# Kore — Plan vivo

> Cursor: lee esto al empezar producto/arquitectura. Actualízalo si cambia fase o decisión.
> Histórico de hitos: [`milestones.md`](./milestones.md) · Backlog abierto: [`TODO.md`](./TODO.md)

| Campo | Valor |
|-------|--------|
| Repo | `jonoyanguren/kore` |
| Producto | **Kore** · hablado **Jone** (`ASSISTANT_NAME`) |
| Fase actual | **Cerrar el piloto** — Stripe, tope LLM, página legal |
| Canal | Consola web = operar / día · Telegram = captura móvil opcional |
| Deploy | Fly.io · `/data` |
| LLM | OpenRouter · modelos según plan: 5=Flash · 10=Flash+Haiku · 20/Jon=híbrido Pro+Haiku · misiones Rápido=Flash / A fondo=v4-pro (en 5, todo Flash) |
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
- [ ] **Cerrar el piloto** *(2026-08-30)* — Stripe + tope LLM; queda legal

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
| D29 | **Preguntar** sobre una misión hecha (2026-08-27): Q&A con el informe; no relanza el loop |
| D30 | **Tono del usuario** (2026-08-30): chips (trato/largo/calidez/humor/firma); onboarding + Más; `/tono` infiere del chat; Gmail reply usa ese perfil (no “como Jon”) |
| D31 | **Cerrar el piloto** (2026-08-30): fase = las 8 tareas técnicas (allowlist, landing, flags, gasto/tope, Stripe, legal). Registro abierto (D14) queda superseded para el piloto |
| D32 | **Modelos según plan** (2026-08-31): Entrar (5) = siempre Flash. Más (10) = Flash diario + Haiku strong. Holgado (20) / Jon / local = híbrido env (Pro diario + Haiku). Mismo producto; el plan cambia modelo y cuánto mes |
| D33 | **Misiones: dos modos** (2026-09-01): **Rápido** (Flash → decisión + siguiente paso) / **A fondo** (Pro → informe denso). Loco/Duro solo en misiones viejas. D26 (4 modos) superseded |

## Roadmap (lean)

**Cerrado Phase 3:** misiones usable + dogfood + UI Resultado.

**Cerrado Calendar (D24/D25):** read primary + crear bloque desde chat. Dogfood aparcado; no más slice ahora.

**Ahora:** **Cerrar el piloto** (D31). Lista en `TODO.md`. Layout 1.6 espera diseño.

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
- [x] Landing pública (logged-out) — hero + Día/Companion/Misiones; Entrar / Crear cuenta + precios
- [x] Consola visual = landing (canvas / papel / tipo / píldoras) — 2026-08-27
- [ ] Rediseño UI layout (diseño externo → maquetar)
- [ ] App móvil día a día (Kore)

## Next steps

1. Cerrar el piloto — las 8 tareas en [`TODO.md`](./TODO.md)
2. Layout 1.6 cuando llegue diseño (no inventar)

No hinchar este archivo: cerrar → `milestones.md` + TODO corto.

## Changelog (reciente)

| Fecha | Cambio |
|-------|--------|
| 2026-09-01 | Intake misiones: ronda 1 siempre pregunta (no saltar si el JSON falla) |
| 2026-09-01 | Admin (Jon/legacy) ve el saldo OpenRouter en Más; `make openrouter-credits` |
| 2026-09-01 | Tope LLM: owner (`legacy_prompts`) sin corte; `make account-cap EMAIL=… USD=0` |
| 2026-09-01 | Skill companion **champion-pool** (`/pool`): marco Pochi/iTero para armar la pool |
| 2026-08-31 | Precios: ejemplo de uso diario en cada plan |
| 2026-08-31 | Registro abierto: el pago es el gate. Allowlist / «Pide acceso» fuera |
| 2026-08-31 | Precios piloto: 5 / 10 / 20 € al mes (tabla landing + paywall). Pack suelto fuera |
| 2026-08-31 | Stripe: Checkout + webhooks (fuente de verdad; firma + idempotencia). 20 € / 10 € |
| 2026-08-31 | Tope LLM de prueba: `$0.50`/mes (antes $20) |
| 2026-08-31 | Piloto: flag `allowed` en cuenta (login/sesión; `make account-off/on`) |
| 2026-08-30 | Piloto: allowlist + landing «Pide acceso» |
| 2026-08-30 | **D31** Fase: **cerrar el piloto** (8 tareas técnicas) |
| 2026-08-30 | Foco → piloto de pago (gate, tope LLM, Stripe) |
| 2026-08-30 | **D30** Tono del usuario: chips + `/tono` + Gmail reply personalizado |
| 2026-08-28 | Misiones: imágenes vía proxy + hide-until-load (sin parpadeo si 404) |
| 2026-08-28 | Board: quitar cards; lista como Día (filas, no cajas) |
| 2026-08-28 | Dogfood intake vago (D27): bastante bien |
| 2026-08-27 | **D29** Preguntar en panel de misión: Q&A sobre el informe |
| 2026-08-27 | Misiones: al abrir una, se oculta el historial; scrollbars invisibles |
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
