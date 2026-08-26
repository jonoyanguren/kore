# Kore — Plan de pruebas (QA)

Documento repetible. Marca `- [ ]` → `- [x]` en cada corrida.

**Gate de ship:** servidor local + pytest + `qa_local.sh` verdes **antes** de commit → push → deploy (ver `.cursor/rules/living-plan.mdc`).

| Campo | Valor |
|-------|--------|
| App local | `http://127.0.0.1:8000` |
| App Fly | `https://kore.fly.dev` |
| Modelo | OpenRouter `xiaomi/mimo-v2.5` |
| Última corrida automatizada | 2026-07-26 — pytest 7 passed; qa_local 9 OK |

## Cómo arrancar local

```bash
cd /Users/jon/Proyectos/kore
uv sync
# si uvicorn falla por shebang viejo:
uv sync --reinstall-package uvicorn
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

En otra terminal:

```bash
curl -sS http://127.0.0.1:8000/healthz   # {"status":"ok"}
uv run pytest -q
./scripts/qa_local.sh                    # humo HTTP → respuesta real a Telegram
```

```bash
# Consola web (Phase 1.5)
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
cd web && npm run dev   # http://127.0.0.1:5173 — email+password (Jon: OWNER_EMAIL + CONSOLE_SECRET)
```

**Nota:** el móvil sigue yendo a Fly salvo que montes un túnel y cambies el webhook. `qa_local.sh` pega al endpoint local y la respuesta llega a tu Telegram real.

---

## A. Automatizado (CI / local)

### A1. Unit tests (`uv run pytest -q`)

- [ ] Skills cargan (incl. dream, tasks, project-status)
- [ ] Fechas: `mañana`, `el lunes que viene`, `el siguiente lunes` resuelven ISO
- [ ] Fechas habladas: hoy/mañana/`el lunes que viene` (sin “Madrid” en clock humano)
- [ ] Command router: `/skills`, `/diario`, `/hora`, chat libre
- [ ] Project docs whitelist + always inject
- [ ] Assembler incluye playbooks de skills
- [ ] Phase 1: vault + tasks + agenda store

### A2. Humo HTTP local (`./scripts/qa_local.sh`)

Requiere servidor local + `.env` completo.

- [ ] `GET /healthz` → 200 `{"status":"ok"}`
- [ ] Webhook sin secret → 403
- [ ] Webhook path malo → 404
- [ ] Mensaje texto → `{"ok":true}` + respuesta en Telegram
- [ ] `/hora` → fecha ES en Telegram
- [ ] `/tareas` → lista o “no hay tareas”
- [ ] `/agenda` → lista o “vacía”
- [ ] Foto+caption / `/dream` → MANUAL

---

## B. Manual en Telegram (Fly o túnel→local)

### B1. Comandos

| # | Acción | Esperado | OK? |
|---|--------|----------|-----|
| B1.1 | `/start` | Saludo + comandos (incl. tareas/agenda/dream) | |
| B1.2 | `/hora` | Fecha ES legible + hora | |
| B1.3 | `/skills` | Lista skills (8+) | |
| B1.4 | `/diario` | Diario del día o “vacío” | |
| B1.5 | `/tareas` | Lista o vacío | |
| B1.6 | `/agenda` | Lista o vacío | |
| B1.7 | `/dream` | Informe de consolidación (cuesta LLM) | |

### B2. Captura / tasks / tono

| # | Acción | Esperado | OK? |
|---|--------|----------|-----|
| B2.1 | Captura con fecha relativa | Confirma corto, sin upsell | |
| B2.2 | `añade tarea QA local para mañana` | Crea tarea; `/tareas` la muestra | |
| B2.3 | `qué modelo llm usas?` | OpenRouter + `xiaomi/mimo-v2.5` | |
| B2.4 | `qué tarea es la siguiente?` (proyecto) | Cita PLAN Phase 1 leftovers / Phase 2, no inventa | |

### B3. Imágenes

| # | Acción | Esperado | OK? |
|---|--------|----------|-----|
| B3.1 | Foto + caption `qué es esto?` | Describe la foto | |
| B3.2 | Foto sola + texto &lt;3s | Responde a la imagen | |

### B4. Negativos

| # | Acción | Esperado | OK? |
|---|--------|----------|-----|
| B4.1 | Otro chat_id | Ignorado | |
| B4.2 | Sticker/audio | Mensaje de “solo texto e imágenes” | |

---

## C. Checklist de regresión rápida (5 min)

1. [ ] `/hora`
2. [ ] `/tareas`
3. [ ] Captura corta sin upsell
4. [ ] Foto+caption `qué es esto?`
5. [ ] `uv run pytest -q` + `./scripts/qa_local.sh` verdes

---

## Resultados (última corrida)

| Fecha | Entorno | pytest | qa_local | Manual B | Notas |
|-------|---------|--------|----------|----------|-------|
| 2026-07-26 | local | 7 passed | 9 OK | Phase 1 en Telegram (revisar msgs) | Gate: QA antes de push/deploy |

## Fallos conocidos / a vigilar

- Foto y texto separados: espera ~3s el follow-up.
- Preferir **caption en la misma foto** para visión.
- Shebang de `.venv/bin/uvicorn` a veces apunta a otro proyecto → `.venv/bin/python -m uvicorn …`
- `/dream` y cron ~09:00 Madrid llaman al LLM; no meter en humo barato.
