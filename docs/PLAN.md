# Kore — Plan vivo

> Cursor: lee esto al empezar producto/arquitectura. Actualízalo si cambia fase o decisión.
> Histórico de hitos: [`milestones.md`](./milestones.md) · Backlog abierto: [`TODO.md`](./TODO.md)

| Campo | Valor |
|-------|--------|
| Repo | `jonoyanguren/kore` |
| Producto | **Kore** · hablado **Jone** (`ASSISTANT_NAME`) |
| Fase actual | **2 — Gmail** (MVP; 1.6 dogfood/UI en paralelo) |
| Canal | Consola web = operar / día · Telegram = captura móvil opcional |
| Deploy | Fly.io · `/data` |
| LLM | OpenRouter · diario `deepseek/deepseek-v4-pro` · strong `claude-sonnet-4.6` (asks gordas + **dream**) |
| Diseño largo | `companion-plan.md` · Consola 1.5: `web-console-plan.md` |

## Estado

- [x] Phase 0 — Kernel + captura
- [x] Phase 1 — Vault / tasks / dream (cron 09:00 Madrid in-process)
- [x] Phase 1.5 — Consola web MVP (chat + board)
- [ ] Phase 1.6 — UX personal *(parcial; ver TODO)*
- [ ] Phase 2 — Gmail
- [ ] Phase 3 — Misiones
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

## Roadmap (lean)

**Ahora — Phase 2 Gmail (MVP):**
1. OAuth Google + refresh en `/data` (D2) — scope **`gmail.modify`** (leer + marcar leídas; no send)
2. Inbox (hoy / unread) + marcar leído vía API / tools
3. Superficie: sección en **vista Día** + comando `/inbox` (chat)
4. Inbox Día = lista unread + **Tarea** (IA) / **Leído** (digest IA en Día aparcado)
5. Dream 09:00 incluye unread Gmail → sección **Inbox** en el briefing
6. Log de triage: mails marcados leídos (vista Día + `list_marked_read`)

**Aplazado en P2:** triage automático a carpetas/labels, envío de mail, multi-cuenta, digest IA en Día.

**Luego:** Misiones (Phase 3, independiente de Gmail) · Git · Calendar.

**1.6:** dogfood OK; UI viva = rediseño aparte; fricciones = miguitas.

Detalle de lo ya shipped → [`milestones.md`](./milestones.md).

## Success (vivo)

- [x] Kernel, tasks, dream 09:00, consola MVP
- [x] Day strip + chat vivo + tareas ricas + layouts + memoria drawer
- [x] Voz one-tap · privacidad · mobile · gasto LLM en barra · proyecto inferido (sin chips)
- [x] Dogfood: briefing en Día + consola como canal principal
- [x] Gmail OAuth + inbox en Día / `/inbox` + dream Inbox + triage log
- [ ] Misión · git (más adelante)

## Next steps

1. **Gmail MVP:** OAuth → `/data` → listar mail → Día + `/inbox`
2. Fricciones dogfood → miguitas en `TODO.md`
3. UI viva = rediseño aparte (no bloquea)

No hinchar este archivo: cerrar → `milestones.md` + TODO corto.

## Changelog (reciente)

| Fecha | Cambio |
|-------|--------|
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
