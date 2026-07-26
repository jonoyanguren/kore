# Kore — Plan de pruebas (QA)

Documento repetible para validar Phase 0. Marca `- [ ]` → `- [x]` en cada corrida.

| Campo | Valor |
|-------|--------|
| App local | `http://127.0.0.1:8000` |
| App Fly | `https://kore.fly.dev` |
| Modelo | OpenRouter `xiaomi/mimo-v2.5` |
| Última corrida automatizada | 2026-07-26 — pytest 4 passed; qa_local 6 OK |

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

**Nota:** el móvil sigue yendo a Fly salvo que montes un túnel y cambies el webhook. `qa_local.sh` pega al endpoint local y la respuesta llega a tu Telegram real.

---

## A. Automatizado (CI / local)

### A1. Unit tests (`uv run pytest -q`)

- [ ] Skills: cargan 5 skills; `/hora` → time-madrid; catálogo no vacío
- [ ] Fechas: `mañana`, `el lunes que viene`, `el siguiente lunes` resuelven ISO
- [ ] Fechas habladas: hoy/mañana/`el lunes que viene` (sin “Madrid” en clock humano)
- [ ] Command router: `/skills`, `/diario`, `/hora`, chat libre

### A2. Humo HTTP local (`./scripts/qa_local.sh`)

Requiere servidor local + `.env` completo.

- [ ] `GET /healthz` → 200 `{"status":"ok"}`
- [ ] Webhook sin secret → 403
- [ ] Webhook path malo → 404
- [ ] Mensaje texto → `{"ok":true}` + respuesta en Telegram en pocos segundos
- [ ] Simular `/hora` vía update → mensaje con fecha ES (día mes año, HH:MM), sin “Europe/Madrid”
- [ ] Foto + caption “qué es esto?” en el mismo update → respuesta sobre la imagen (no ITV random)

---

## B. Manual en Telegram (Fly o túnel→local)

Hazlo en chat limpio o con contexto reciente conocido. Anota OK / FAIL.

### B1. Comandos

| # | Acción | Esperado | OK? |
|---|--------|----------|-----|
| B1.1 | `/start` | Saludo corto + comandos | |
| B1.2 | `/hora` | Fecha ES legible + hora, sin “Madrid/CEST” | |
| B1.3 | `/skills` | Lista skills | |
| B1.4 | `/diario` | Diario del día o “vacío” | |

### B2. Captura y tono

| # | Acción | Esperado | OK? |
|---|--------|----------|-----|
| B2.1 | `recuerda que tengo reunión el siguiente lunes a las 11` | Una línea tipo “Apuntado… el lunes que viene a las 11”. Sin “si quieres te armo un plan”. Sin ISO en el chat | |
| B2.2 | `/diario` o preguntar qué tiene apuntado | Aparece el recuerdo (ISO puede estar en DB; en chat habla natural) | |
| B2.3 | Charla “quién eres” | Respuesta corta, no elevator pitch eterno | |
| B2.4 | `qué modelo llm usas?` | Menciona OpenRouter + `xiaomi/mimo-v2.5` | |

### B3. Imágenes

| # | Acción | Esperado | OK? |
|---|--------|----------|-----|
| B3.1 | Foto con **caption** `qué es esto?` (misma burbuja) | Describe/identifica el contenido de la foto | |
| B3.2 | Foto sola y en &lt;3s texto `qué es esto?` | Misma idea: responde a la imagen, no a memoria random | |
| B3.3 | Screenshot de un doc (ej. PLAN) + `qué es esto?` | Resume el doc; **no** guarda next steps en memoria; **no** saca ITV | |
| B3.4 | Foto irrelevante sin pedir guardar | Describe breve; no “Listo, guardado…” | |

### B4. Negativos / seguridad

| # | Acción | Esperado | OK? |
|---|--------|----------|-----|
| B4.1 | Mensaje desde otro chat_id | Ignorado (sin respuesta) | |
| B4.2 | Sticker/audio | “Por ahora entiendo texto e imágenes…” | |

---

## C. Checklist de regresión rápida (5 min)

1. [ ] `/hora`
2. [ ] Captura con fecha relativa (1 línea, sin upsell)
3. [ ] Foto+caption `qué es esto?`
4. [ ] `qué modelo usas?`
5. [ ] `uv run pytest -q` verde

---

## Resultados (última corrida)

| Fecha | Entorno | pytest | qa_local | Manual B | Notas |
|-------|---------|--------|----------|----------|-------|
| 2026-07-26 | local | 4 passed | 6 OK | pendiente B1–B3 en Telegram | Foto visión = manual (file_id real) |

## Fallos conocidos / a vigilar

- Foto y texto en mensajes separados: el servidor espera ~3s el follow-up; si tarda más, la foto se describe sola y el texto puede ir sin imagen.
- Preferir **caption en la misma foto** para visión.
- Shebang de `.venv/bin/uvicorn` a veces apunta a otro proyecto → usar `.venv/bin/python -m uvicorn …` o `uv sync --reinstall-package uvicorn`.
