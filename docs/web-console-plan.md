# Phase 1.5 — Consola web (plan de implementación)

> Plan vivo de producto: [`PLAN.md`](./PLAN.md) · backlog: [`TODO.md`](./TODO.md)  
> Estado: **aprobado en idea** · código: **aún no**  
> Fecha: 2026-07-27

## Por qué ahora

Telegram vale para captura móvil. Se queda corto para **operar** (tareas, checks, QA, listas). Una consola web acelera dogfood del resto (dream, Gmail, misiones) sin sustituir el bot.

## Objetivo v1

Una sola app Fly (`kore.fly.dev`) con:

1. **Chat texto** — mensaje → mismo `LLMAssistant.ask` que Telegram → respuesta (sin imágenes/adjuntos en v1; voz = fase siguiente de la misma UI).
2. **Panel tareas** — En curso / Pendientes; completar; cambiar estado/proyecto/url; links clicables.
3. **Auth mínima** — 1 usuario (tú).
4. **Frontend Vite** desde el día 1 (base para UI potente: voz/transcripción, etc. más adelante).

Telegram sigue igual. Misma SQLite `/data/kore.db` y vault.

## Fuera de v1 (misma app Vite, slices posteriores)

- Voz / micrófono / transcripción (Whisper u OpenRouter audio) — **previsto**, no en el primer ship
- Imágenes, stickers, inline keyboards
- Streaming token-a-token / WebSocket
- Multi-usuario, PWA offline perfecta
- Agenda/diario/dream UI (1.5.1+)
- Paridad de comandos slash en la web (panel tareas + chat libre bastan)

## Arquitectura

```
Browser (Vite React SPA → web/dist)
    │  cookie / Bearer CONSOLE_SECRET
    ▼
FastAPI  /api/*  +  StaticFiles(web/dist)
    │
    ├─ MemoryStore (tasks CRUD) + vault sync en writes
    └─ LLMAssistant.ask(text)   ← mismo kernel / tools / historial sesión
Telegram webhook (sin cambios de producto)
```

**Principio:** no duplicar lógica de negocio. Extraer solo lo mínimo si `handle_text_message` está demasiado acoplado a Telegram.

**Stack UI (D13):** **Vite + React + TypeScript** desde el principio. No vanilla “para luego migrar”. v1 es chat+tareas; la misma SPA absorbe voz/transcripción después.

### Auth (D12 — decisión al implementar)

Recomendación v1:

| Campo | Valor |
|-------|--------|
| Secret | `CONSOLE_SECRET` (env / Fly secret), `openssl rand -hex 32` |
| Login | `POST /api/login` con `{ "secret": "..." }` → cookie httpOnly `kore_console` |
| API | Cookie **o** `Authorization: Bearer …` (mismo secret) |
| Fail | 401 en `/api/*`; estáticos públicos solo la página de login |

Alternativa: reutilizar `CRON_SECRET` — **no** (mezcla cron y UI).

### API HTTP (delgada)

| Método | Ruta | Qué hace |
|--------|------|----------|
| `POST` | `/api/login` | Set cookie |
| `POST` | `/api/logout` | Clear cookie |
| `GET` | `/api/me` | `{ ok: true }` si auth |
| `GET` | `/api/tasks?status=open` | `list_tasks` → JSON (`open` = open+in_progress) |
| `POST` | `/api/tasks` | `add_task` + vault sync |
| `PATCH` | `/api/tasks/{id}` | `update_task` + vault sync |
| `POST` | `/api/tasks/{id}/complete` | `complete_task` + vault sync |
| `DELETE` | `/api/tasks/{id}` | `delete_task` (cancel) + vault sync |
| `POST` | `/api/chat` | `{ "text": "..." }` → `{ "reply": "..." }` vía `llm.ask` |
| `GET` | `/api/messages?limit=40` | historial sesión del día (opcional v1, útil para pintar chat) |

JSON de tarea = campos de `TaskRow` (`id`, `title`, `status`, `due_at`, `priority`, `notes`, `url`, `project`).

Writes de tareas: reutilizar `sync_tasks_vault` de `app/storage/task_tools.py`.

### Frontend v1

- **Stack:** `web/` = Vite + React + TypeScript (SPA).
- **Dev:** `cd web && npm run dev` (proxy `/api` → `127.0.0.1:8000`).
- **Prod:** `npm run build` → `web/dist`; FastAPI sirve `web/dist` en `/`.
- **Layout:** dos columnas desktop (chat | tareas); stacked en móvil.
- **Chat:** mensajes + input; estado “pensando…” en `POST /api/chat` (timeout largo).
- **Tareas:** board tipo Trello (En curso / Pendientes / Hechas) con drag & drop (`@dnd-kit`); check → complete; links.
- **Voz (post-v1):** MediaRecorder → endpoint transcribe → texto al input/chat (misma SPA).

Sin Next.js / SSR. Una SPA estática detrás de FastAPI basta.

### Deploy / Docker

- Multi-stage Dockerfile:
  1. `node` stage: `npm ci && npm run build` en `web/`
  2. `python` stage: copia `web/dist` → `/app/web/dist`
- `app.mount("/", StaticFiles(directory="web/dist", html=True), name="web")` **después** de `/api` y `/healthz`.
- SPA fallback: `html=True` o ruta catch-all a `index.html` (rutas client-side si las hay).
- Fly: secret `CONSOLE_SECRET`; sin máquina extra.
- URL: `https://kore.fly.dev/`

### Persistencia / historial

- `llm.ask` ya guarda user/assistant en `messages` (sesión Madrid) → el chat web **comparte** historial con Telegram del mismo día. Eso es feature, no bug.
- Si molesta mezclar canales más adelante: campo `source=web|telegram` (post-v1).

## Cortes de implementación (cuando digamos “vamos”)

| Slice | Entrega | Demo |
|-------|---------|------|
| **A** | Scaffold Vite+React+TS + `CONSOLE_SECRET` + auth + API tasks + tests | curl completa una tarea |
| **B** | UI React tareas (secciones, check, edit, links) + proxy dev | browser local: check → done |
| **C** | `POST /api/chat` + UI chat | mensaje web → misma voz/tools que Telegram |
| **D** | historial messages, Docker multi-stage, Fly secret + deploy | dogfood en `kore.fly.dev` |
| **E+** | Voz / transcripción (cuando toque) | mic → texto → chat |

## Archivos previstos

```
web/                       # Vite + React + TS (package.json, src/, …)
web/dist/                  # build output (gitignored; generado en Docker/CI)
app/config.py              # console_secret
app/web/auth.py            # cookie/bearer verify
app/web/api.py             # router /api/*
app/main.py                # include_router + StaticFiles(web/dist)
tests/test_web_api.py
docs/QA.md                 # sección consola (uvicorn + vite / build)
.env.example               # CONSOLE_SECRET=
Dockerfile                 # multi-stage node build + python
```

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Build Node en cada deploy | layer cache `web/package-lock.json`; multi-stage |
| Chat lento / timeout proxy | timeout UI alto; “pensando…”; no streaming v1 |
| Secret filtrado | solo env/Fly; nunca en bundle JS |
| Estáticos tapan `/healthz` | montar StaticFiles al final |
| Scope creep voz en v1 | voz = slice E+; v1 solo texto + tareas |
| Commands `/dream` solo Telegram | OK v1 |

## Success criteria

- [ ] Login con secret; sin secret → 401 en API
- [ ] Completar / editar tarea en la web en <2 clics
- [ ] Chat texto round-trip con tools (p.ej. “añade tarea X”)
- [ ] Misma DB que Telegram; `/tareas` en bot sigue coherente
- [ ] pytest + curl/QA local verdes antes de deploy

## Next

Cuando digas **vamos**: empezar por **slice A** (scaffold Vite + API tasks + auth).
