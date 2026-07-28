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
| LLM | OpenRouter · diario `deepseek/deepseek-v4-pro` · strong `claude-sonnet-4.6` (asks gordas + **dream**) |
| Diseño largo | `companion-plan.md` · Consola 1.5: `web-console-plan.md` |

## Estado

- [x] Phase 0 — Kernel + captura
- [x] Phase 1 — Vault / tasks / dream (cron 09:00 Madrid in-process)
- [x] Phase 1.5 — Consola web MVP (chat + board)
- [ ] Phase 1.6 — UX personal *(parcial; UI viva aparte / fricciones)*
- [x] Phase 2 — Gmail MVP
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
| D16 | Gmail MVP = OAuth + Día/`/inbox` + dream Inbox + triage log |
| D17 | Gmail send = **reply/answer**: leer hilo → borrador IA editable → confirmar → enviar (`gmail.send`; no compose frío en v1) |
| D18 | Misión = **input → loop → output**; no bloquea chat; pantalla Misiones; resultado = markdown bonito en vault |

## Roadmap (lean)

**Ahora — Phase 3 Misiones (D18):**

Una misión no es “un botón mágico”: es capacidad de Kore + pantalla.

| Fase | Qué | UI |
|------|-----|----|
| **Input** | Brief + preguntas hasta tener el encargo claro → se **lanza** | Chat (o formulario corto) |
| **Loop** | Itera en background (puede retomar cada X tiempo) hasta resultado usable; **no bloquea** chat | Estado en pantalla Misiones |
| **Output** | Resultado = markdown **bien formateado** en vault; clic en misión → lectura | Pantalla Misiones (activas / hechas) |

Ejemplo: “casas en Cantabria con X” → aclara → loop research → informe `.md`.

**MVP build (orden):**
1. Modelo + persistencia (`missions` + `vault/missions/…`)
2. Layout **Misiones** (lista + detalle markdown)
3. Input: aclarar en chat → crear misión `queued`
4. Runner in-process (cola, max 1): ticks del loop + checkpoints
5. Primera misión real (p.ej. perfil tono desde sent, o research stub)

**Gmail:** cerrado (MVP + D17). Parking aparte. Dogfood reply en paralelo.

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

1. **Phase 3 — Misiones:** esqueleto (modelo + pantalla + runner stub)
2. Dogfood Gmail reply en paralelo (fricciones → TODO)
3. UI viva = rediseño aparte (no bloquea)

No hinchar este archivo: cerrar → `milestones.md` + TODO corto.

## Changelog (reciente)

| Fecha | Cambio |
|-------|--------|
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
