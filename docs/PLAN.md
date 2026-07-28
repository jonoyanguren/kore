# Kore — Plan vivo

> Cursor: lee esto al empezar producto/arquitectura. Actualízalo si cambia fase o decisión.
> Histórico de hitos: [`milestones.md`](./milestones.md) · Backlog abierto: [`TODO.md`](./TODO.md)

| Campo | Valor |
|-------|--------|
| Repo | `jonoyanguren/kore` |
| Producto | **Kore** · hablado **Jone** (`ASSISTANT_NAME`) |
| Fase actual | **1.6 UX personal** (código P1 hecho; falta dogfood) |
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
| D2 | Gmail OAuth → `/data` |
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

**1.6 restante:** dogfood (vista Día 09:00 + consola como canal).

**2+:** Gmail digest · misiones · git confirmado · calendar/PDF.

Detalle de lo ya shipped → [`milestones.md`](./milestones.md).

## Success (vivo)

- [x] Kernel, tasks, dream 09:00, consola MVP
- [x] Day strip + chat vivo + tareas ricas + layouts + memoria drawer
- [x] Voz one-tap · privacidad · mobile · gasto LLM en barra · proyecto inferido (sin chips)
- [ ] Dogfood: briefing en Día + consola como canal principal
- [ ] Gmail · misión · git (más adelante)

## Next steps

1. **Hoy:** `/dream` o catch-up post-deploy → validar briefing en vista Día (P0)
2. **Dogfood** consola (chat limpio + mic + board + Memoria)
3. Phase 2: Gmail cuando el loop diario esté asentado

No hinchar este archivo: cerrar → `milestones.md` + TODO corto.

## Changelog (reciente)

| Fecha | Cambio |
|-------|--------|
| 2026-07-28 | Dream → modelo strong (Sonnet); vacío ≠ ok; catch-up si vault `(vacío)` |
| 2026-07-27 | Close noche: DeepSeek diario, chip gasto, sin espacios UI |
| 2026-07-27 | Close sesión tarde: P1 en Fly; next = dogfood Día |
| 2026-07-27 | P1: voz / espacios / privacidad / mobile |
| 2026-07-27 | Split PLAN/TODO ↔ `milestones.md` (contexto histórico) |
| 2026-07-27 | Día = canal briefing; agenda `01-Ago` + ventana 3 días; ★ / must-not-miss |
| 2026-07-27 | Archivar completadas → `vault/tasks/done.md` |
| 2026-07-27 | Cron dream in-process 09:00 Madrid |

Histórico largo anterior → entradas en `milestones.md`.
