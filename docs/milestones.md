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
- **Espacios** — retirados; el modelo infiere `project` en tareas (filtro board vía ⌘K)
- **Privacidad** — overview, export vault `.zip`, borrar categoría de memoria
- Mobile polish + empty states en chat/board/drawer

Pendiente 1.6 → UI viva (aparte) / fricciones dogfood.

## 2026-07-28 — Dogfood consola

- Jon opera Día / Chat / Board a diario en Fly
- Dream strong (Sonnet); sin `add_task` (no resucitar archivadas)
- Chrome limpio: una vista, Más drawer, chips proyecto, fechas humanas

## 2026-07-28 — Phase 2 Gmail MVP (cerrado)

- OAuth Google (`gmail.modify`) + refresh tokens en `/data`
- Cliente: list unread + marcar leído
- Vista Día: Inbox (lista) + **Leído** + **Tarea** (IA + link mail)
- Chat `/inbox` + skill companion
- Dream 09:00 → unread en sección **Inbox** del briefing
- Log triage: `gmail_marked_read.jsonl` + Día «Marcados leídos hoy» + tool `list_marked_read`
- Aplazado (Parking): triage auto labels, send, multi-cuenta, digest IA Día

## 2026-07-28 — Gmail D17 reply

- Scope OAuth + `gmail.send` (reconectar una vez)
- Día: **Responder** → LLM borrador editable → **Enviar**
- API: `POST .../reply-draft` + `POST .../reply`
- Sin compose frío ni send desde chat

## 2026-07-28 — Phase 3 Misiones (esqueleto)

- 4º layout **Misiones** (tecla 4)
- SQLite `missions` / `mission_events` + `vault/missions/{id}.md`
- Nueva (formulario) → cola → runner stub con ticks → markdown
- Ocultar terminadas · cancelar · max 1 running

## 2026-07-28…29 — Phase 3 Misiones (loop real + coste)

- Research web real (`web_search`/`fetch`) en ticks; Relanzar; detalle split
- Coste: misiones → DeepSeek; strong dogfood → Haiku 4.5; prompt cache en loops
- Más drawer: tabla Modelos (Daily/Strong + ~/1M)
- Nueva: aclaración 1–2 preguntas (DeepSeek) antes de Lanzar

## 2026-07-30…08-09 — Misiones calidad + extras

- Normal/Pro (Flash/Pro) + imágenes en markdown de misión
- D22: plan → N tareas + handoff; informe con links/tablas
- `/entrevista` + `list_memory`; Copiar URL en tareas
- Móvil: Expo M0 + contenido Día/Captura/Tareas/Misiones (Plataforma)

## 2026-08-10 — Dream fiable

- Consola: `/dream` / `/sueno` ejecuta el runner (antes solo iba al LLM)
- Reintento con modelo daily si el strong falla/vacío
- Fallback determinista (tareas/agenda/calendar/inbox) → Día nunca vacío
- Cron reintenta si el vault quedó en fallback

## 2026-08-10 — Chat → crear bloque Calendar (D25)

- OAuth `calendar.events` (+ readonly); flag `calendar_can_write`
- Tool `create_calendar_block` crea en primary al momento (sin card confirm)
- Pregunta solo si día/hora ambiguos; no validar con `list_calendar` antes
- Tras deploy: **Reconectar** Google una vez

## 2026-08-10 — Google Calendar read (D24)

- Scope `calendar.readonly` en OAuth Google (mismo token que Gmail)
- Client: todos los calendarios `selected`; eventos live (no SQLite)
- Día Reuniones: merge Google + agenda local; dream + PromptAssembler + tool `list_calendar`
- Tras deploy: habilitar Calendar API en GCP + Reconectar en Más

## 2026-08-10 — Phase 3 cerrado · dogfood fin · sin Git en Kore

- Dogfood Phase 0–3 **cerrado** (consola + Gmail + Misiones en uso real)
- Misiones UX: summary pass → `## Resultado`; card Resultado + accordion investigación; bloques de color + tablas tipo card
- **D3 supersede:** Git/código / programar desde móvil = **proyecto aparte**; no Phase 4 en Kore
- Siguiente: elegir feature nueva (no más fase dogfood)

## 2026-08-26 — Misiones modos (D26)

- Nueva: Normal / Loco / Experto / Duro (sustituye Calidad Normal/Pro)
- Leyenda visible en el form; modelo: Normal=Flash, resto=Pro
- Prompts de plan / tarea / Resultado / aclarar cambian con el modo
- Legacy `pro` → Experto

## 2026-08-26 — Cuentas aisladas (D14 superseded)

- Registro abierto email+password (sin invitaciones)
- Un SQLite + vault por usuario; `accounts.db` compartido
- Bootstrap: Jon hereda `/data/kore.db` → `users/{id}/`
- Onboarding: nombre + tono; Telegram sigue siendo Jon

## 2026-08-27 — Landing pública

- Logged-out: hero (claim + mock Día) + bandas Día / Companion / Misiones
- Overlay Entrar / Crear cuenta (mismos endpoints); cookie → consola
- Mock de producto ficticio (no captura real)

## 2026-08-27 — Consola visual = landing

- Tokens compartidos: canvas `#12151a`, paper `#f3efe8`, accent `#2f6f5e`, Instrument Sans
- Consola = dispositivo papel sobre canvas (como el mock del hero)
- Onboarding en card tipo overlay; drawers/⌘K con blur oscuro

## Prompting (baseline cerrado)

- `personality.md`, `kimay.md`, Datafine, `slow-project.md`, `investing.md` (azValor baseline)
- Kimay = prompt propio (no meter todo en personality)

---

*Última actualización del archivo: 2026-08-27*
