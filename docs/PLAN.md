# Kore — Plan vivo

> Cursor: lee esto al empezar producto/arquitectura. Actualízalo si cambia fase o decisión.
> Histórico de hitos: [`milestones.md`](./milestones.md) · Backlog abierto: [`TODO.md`](./TODO.md)

| Campo | Valor |
|-------|--------|
| Repo | `jonoyanguren/kore` |
| Producto | **Kore** · hablado **Jone** (`ASSISTANT_NAME`) |
| Fase actual | **Agenda + Google Calendar (read)** — post–Phase 3 |
| Canal | Consola web = operar / día · Telegram = captura móvil opcional |
| Deploy | Fly.io · `/data` |
| LLM | OpenRouter · diario `deepseek/deepseek-v4-pro` · strong `claude-haiku-4.5` · misiones Normal=`deepseek-v4-flash` / Pro=`deepseek-v4-pro` · prompt cache en tool loops |
| Diseño largo | `companion-plan.md` · Consola 1.5: `web-console-plan.md` |
| Backlog | `TODO.md` · **Producto** vs **Plataforma** |

## Estado

- [x] Phase 0 — Kernel + captura
- [x] Phase 1 — Vault / tasks / dream (cron 09:00 Madrid in-process)
- [x] Phase 1.5 — Consola web MVP (chat + board)
- [ ] Phase 1.6 — UX personal *(parcial; rediseño en curso con diseñadora → luego maquetar)*
- [x] Phase 2 — Gmail MVP
- [x] Phase 3 — Misiones *(MVP + dogfood + UI Resultado)*
- [ ] ~~Phase 4 — Git / código~~ → **fuera de Kore** (proyecto aparte: programar desde el móvil)
- [ ] Agenda + Google Calendar *(read; en curso)*
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
| D14 | 1.6 = super-herramienta personal; no multi-user |
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

## Roadmap (lean)

**Cerrado Phase 3:** misiones usable + dogfood + UI Resultado.

**Ahora — Agenda + Google Calendar (D24):**

| Slice | Qué |
|-------|-----|
| OAuth | Añadir `calendar.readonly`; Reconectar en Más (una vez) |
| Client | `events.list` solo calendario **primary** |
| Día / dream | Merge Reuniones: Google + `agenda_items` local |
| Chat | Tool `list_calendar`; PromptAssembler contexto |

**No v1:** escribir en GCal, sync → SQLite, multi-cuenta.

**1.6 / UI:** rediseño externo → maquetar cuando llegue.

**App móvil Kore:** captura / Día / audio — **no** sustituye el proyecto de programar desde el móvil.

Detalle shipped → [`milestones.md`](./milestones.md).

## Success (vivo)

- [x] Kernel, tasks, dream 09:00, consola MVP
- [x] Day strip + chat vivo + tareas ricas + layouts + memoria drawer
- [x] Voz · privacidad · gasto LLM · proyecto inferido
- [x] Dogfood consola + Gmail + Misiones
- [x] Phase 3 Misiones usable
- [ ] Google Calendar read en Día / dream / chat (D24)
- [ ] Rediseño UI (diseño externo → maquetar)
- [ ] App móvil día a día (Kore)

## Next steps

1. Lock calendarios (primary vs todos) → implementar D24
2. Cuando llegue el diseño: maquetación UI 1.6
3. App móvil Kore: M2 cuando toque (paralelo, no bloquea)

No hinchar este archivo: cerrar → `milestones.md` + TODO corto.

## Changelog (reciente)

| Fecha | Cambio |
|-------|--------|
| 2026-08-10 | **D24 shipped (code):** Calendar read — todos calendarios visibles; Día/dream/tool; reconectar OAuth |
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
