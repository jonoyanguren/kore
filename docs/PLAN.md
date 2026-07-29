# Kore — Plan vivo

> Cursor: lee esto al empezar producto/arquitectura. Actualízalo si cambia fase o decisión.
> Histórico de hitos: [`milestones.md`](./milestones.md) · Backlog abierto: [`TODO.md`](./TODO.md)

| Campo | Valor |
|-------|--------|
| Repo | `jonoyanguren/kore` |
| Producto | **Kore** · hablado **Jone** (`ASSISTANT_NAME`) |
| Fase actual | **3 — Misiones** (D18: input → loop → output + pantalla) |
| Canal | Consola web = operar / día · Telegram = captura móvil opcional |
| Deploy | Fly.io · `/data` |
| LLM | OpenRouter · diario `deepseek/deepseek-v4-pro` · strong `claude-haiku-4.5` (dogfood; alt Kimi/Sonnet) · prompt cache en tool loops |
| Diseño largo | `companion-plan.md` · Consola 1.5: `web-console-plan.md` |

## Estado

- [x] Phase 0 — Kernel + captura
- [x] Phase 1 — Vault / tasks / dream (cron 09:00 Madrid in-process)
- [x] Phase 1.5 — Consola web MVP (chat + board)
- [ ] Phase 1.6 — UX personal *(parcial; UI viva aparte / fricciones)*
- [x] Phase 2 — Gmail MVP
- [ ] Phase 3 — Misiones *(build MVP shipped; dogfood aclaración + 1ª útil)*
- [ ] Phase 4 — Git / código
- [ ] Phase 5+ — Calendar, PDF, media web…

## Decisiones (cerradas)

| # | Valor |
|---|--------|
| D1 | Companion kernel |
| D2 | Gmail OAuth (`gmail.modify`) → `/data` |
| D3 | Git: este repo primero |
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
| D17 | Gmail send = **reply/answer**: leer hilo → borrador IA editable → confirmar → enviar (`gmail.send`; no compose frío en v1) |
| D18 | Misión = input → loop → output; no bloquea chat; resultado markdown en vault |
| D19 | Misiones UI: **4º layout**; lista + «Ocultar terminadas»; **Nueva** inicia el input (no chat-first) |
| D20 | Persistencia: **SQLite** lista/estado · **vault** `missions/{id}.md` = output |
| D21 | Loop: ticks en el tiempo (`next_run_at`); runner in-process; max 1 activa v1 |
| D22 | Misiones: **plan → N tareas**; handoff corto entre tareas (no markdown entero) |

## Roadmap (lean)

**Ahora — Phase 3 Misiones (D18–D21):**

| Fase | Qué | UI |
|------|-----|----|
| **Input** | Brief + preguntas hasta claro → **Lanzar** | Layout Misiones → **Nueva** |
| **Loop** | Ticks cada cierto tiempo hasta resultado usable; **no bloquea** chat | Estado en la lista |
| **Output** | Markdown bonito en vault; clic → lectura | Misma pantalla |

**Cerrado:** 4º layout · SQLite listado · vault output · Nueva (formulario v1) · ocultar terminadas · cancelar · stub ticks.

**Siguiente slice:** dogfood aclaración + primera misión útil; tono sent (parking).

**MVP build:**
1. [x] Tabla `missions` + vault path
2. [x] Layout Misiones (lista, ocultar hechas, detalle md, Nueva)
3. [x] Runner ticks + `next_run_at`
4. [x] Tools reales + aclaración en Nueva
5. Jon prueba con una misión

**Gmail:** cerrado. Dogfood reply en paralelo.

**1.6:** dogfood OK; UI viva = rediseño aparte; fricciones = miguitas.

Detalle de lo ya shipped → [`milestones.md`](./milestones.md).

## Success (vivo)

- [x] Kernel, tasks, dream 09:00, consola MVP
- [x] Day strip + chat vivo + tareas ricas + layouts + memoria drawer
- [x] Voz one-tap · privacidad · mobile · gasto LLM en barra · proyecto inferido (sin chips)
- [x] Dogfood: briefing en Día + consola como canal principal
- [x] Phase 2 Gmail MVP cerrado
- [ ] Misiones (Phase 3)
- [ ] Git (Phase 4)

## Next steps

1. Dogfood **Nueva** en Fly (Continuar → preguntas → Lanzar → informe)
2. Mirar gasto OpenRouter (Haiku strong + DeepSeek misiones)
3. Dogfood Gmail reply en paralelo

No hinchar este archivo: cerrar → `milestones.md` + TODO corto.

## Changelog (reciente)

| Fecha | Cambio |
|-------|--------|
| 2026-07-29 | Ledger LLM: tabla `llm_spend` + Más drawer (hoy/7d/por kind) |
| 2026-07-29 | D22: misiones por tareas (plan auto + handoff + checklist UI) |
| 2026-07-29 | Misiones: markdown con links/tablas en panel; 3 ticks; informe no cortado |
| 2026-07-29 | Misiones Nueva: aclaración 1–2 preguntas (DeepSeek) antes de Lanzar |
| 2026-07-28 | Strong → Haiku 4.5 (dogfood); prompt cache + session_id en tool loops |
| 2026-07-28 | Misiones: ticks con **daily** (DeepSeek) mientras dogfood — Sonnet salía ~$2+/misión |
| 2026-07-28 | Misiones: loop con web_search/fetch + strong model; Relanzar |
| 2026-07-28 | Misiones esqueleto: layout + SQLite/vault + runner stub + cancelar |
| 2026-07-28 | D19–D21: Nueva en layout Misiones; SQLite+vault; ticks en el tiempo; ocultar terminadas |
| 2026-07-28 | D18: misión = input → loop → output; pantalla Misiones; markdown resultado |
| 2026-07-28 | Dogfood focus: Gmail reply (D17) estos días; misiones después |
| 2026-07-28 | D17 shipped: Responder en Día (borrador editable + gmail.send) |
| 2026-07-28 | D17: Gmail send = reply/answer (borrador editable), no compose frío |
| 2026-07-28 | **Phase 2 Gmail MVP cerrado** → siguiente = Misiones |
| 2026-07-28 | Gmail triage log: marcados leídos (Día + tool) |
| 2026-07-28 | Dream incluye Gmail unread → sección Inbox en briefing |
| 2026-07-28 | Gmail Día: lista + botón Tarea (IA); digest IA aparcado |
| 2026-07-28 | Gmail: digest IA de unread en vista Día (caché 30 min) |
| 2026-07-28 | Gmail scope = `gmail.modify` (marcar leídas); esqueleto OAuth |
| 2026-07-28 | Phase 2 = Gmail MVP (OAuth + Día/`/inbox`; triage auto aparcado) |
| 2026-07-28 | UI polish pass 1: menos cabeceras; Board Lista/Columnas; Día chips |
| 2026-07-28 | Dogfood marcado hecho (Jon usa consola a diario) |
| 2026-07-28 | Dream sin `add_task` + dedupe vs done.md (no resucitar archivadas) |
| 2026-07-28 | Dream → modelo strong (Sonnet); vacío ≠ ok; catch-up si vault `(vacío)` |
| 2026-07-27 | Close noche: DeepSeek diario, chip gasto, sin espacios UI |
| 2026-07-27 | Close sesión tarde: P1 en Fly; next = dogfood Día |
| 2026-07-27 | P1: voz / espacios / privacidad / mobile |
| 2026-07-27 | Split PLAN/TODO ↔ `milestones.md` (contexto histórico) |
| 2026-07-27 | Día = canal briefing; agenda `01-Ago` + ventana 3 días; ★ / must-not-miss |
| 2026-07-27 | Archivar completadas → `vault/tasks/done.md` |
| 2026-07-27 | Cron dream in-process 09:00 Madrid |

Histórico largo anterior → entradas en `milestones.md`.
