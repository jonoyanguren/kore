# Kore — Milestones (contexto histórico)

> Lo **hecho** vive aquí para no hinchar `PLAN.md` / `TODO.md`.
> Plan vivo: [`PLAN.md`](./PLAN.md) · Backlog abierto: [`TODO.md`](./TODO.md)
> Closes de sesión Cursor: [`closes/`](./closes/)

Convención: añadir un bloque por hito (fecha + bullets). No duplicar el diseño largo (`companion-plan.md`).

---

## 2026-07-26 — Phase 0 kernel + captura

- Repo `kore`, nombre hablado Jone (`ASSISTANT_NAME`)
- Prompts + skills companion; PromptAssembler / SkillRegistry / CommandRouter
- Memoria por categoría, diario, mensajes de sesión (Madrid)
- Imágenes Telegram → MIMO
- Tools capture / time / brainstorm / plan / execute
- QA: `docs/QA.md`, pytest, `scripts/qa_local.sh`
- Inject PLAN/TODO/agent-rules + `read_project_doc`
- Ship: QA local → commit → push → fly deploy
- Skills split: `companion/` (bot) vs `dev/` (Cursor); `open` / `close` + `docs/closes/`

## 2026-07-26…27 — Phase 1 MVP (vault / tasks / dream)

- Vault write-through (`memory/`, `diary/`, `agenda/`, `dreams/`, `tasks/`)
- Tasks + agenda SQLite; status / project / url / notes
- Dream consolidación + briefing; cron → in-process **09:00 Madrid** (HTTP manual opcional)
- `/tareas` En curso → Pendientes; links visibles

## 2026-07-27 — Phase 1.5 consola web MVP

- Auth `CONSOLE_SECRET`; Vite+React+TS
- Board DnD + chat texto (`/api/chat`, `/api/messages`)
- Docker multi-stage; `web/dist` desde FastAPI; Fly

## 2026-07-27 — Phase 1.6 (parcial) UX personal

Hecho en consola:

- Day strip (briefing, resumen, agenda ventana corta `01-Ago`)
- Chat vivo (SSE status + Abrir / En curso / Hecha)
- Tarjeta tarea editable + filtros + buscar
- Lista / board; ★ en curso / check done; DnD con persistencia
- Archivar completadas → `vault/tasks/done.md` (contexto Jone)
- ⌘K; layouts Día / Chat / Board (Momentum)
- Drawer memoria/diario; toasts
- Docs UI (skills + comandos)
- Día: ★ En curso + «No se pueden escapar» (dream / due / prio)
- Canal matutino = **vista Día** (`DREAM_NOTIFY_TELEGRAM=false` por defecto)
- **Voz one-tap** — MediaRecorder → `POST /api/transcribe` (OpenRouter Whisper) → input chat
- **Espacios** — Todo / Personal / Kimay / Kore (filtro board + hint chat + default project)
- **Privacidad** — overview, export vault `.zip`, borrar categoría de memoria
- Mobile polish + empty states en chat/board/drawer

Pendiente 1.6 → dogfood (P0 en `TODO.md`).

## Prompting (baseline cerrado)

- `personality.md`, `kimay.md`, Datafine, `slow-project.md`, `investing.md` (azValor baseline)
- Kimay = prompt propio (no meter todo en personality)

---

*Última actualización del archivo: 2026-07-27*
