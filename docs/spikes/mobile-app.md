# App móvil Kore — producto (Expo)

Carril: **Plataforma**. Distinto de la consola web / PWA.

## Decisiones (cerradas)

| # | Valor |
|---|--------|
| Stack | **Expo** (iOS + Android desde M0) |
| Repo | `mobile/` en monorepo kore |
| Auth | Bearer `CONSOLE_SECRET` → SecureStore |
| Audio UI | Push-to-talk vs continuo → **decidir en M2** (scaffold primero) |
| Ingest audio | Cada nota → **todo lo que haga falta** (diario, memoria, tareas, …) vía clasificar post-transcribe |
| Tareas / misiones | ≈ web adaptada |
| Diferenciador | **Modo audio** (sin chat) |

## Intención

App de **uso diario en el teléfono** con UX propia — no “la consola en chiquito”.

- Web = operar (board, misiones gordas, Gmail, Más…).
- Móvil = captura + día + tareas/misiones reconocibles.
- **Modo audio** = la superficie que no existe en web.

## Superficies

| Tab | Rol | Fase |
|-----|-----|------|
| **Día** | Briefing compacto | M1 |
| **Audio** | Notas de voz encadenadas, sin chat | M2 |
| **Tareas** | Lista / check ≈ web | M1 |
| **Misiones** | Lista + estado + informe ≈ web | M3 |

### Modo audio

- Grabas / sueltas notas una detrás de otra.
- Sin hilo de mensajes ni “esperar respuesta” a cada frase.
- Tras transcribir: el backend (o un paso LLM) reparte a diario / memoria / tareas según contenido.
- Feedback mínimo en UI; resumen de sesión = opcional más tarde.

## Arquitectura

```
mobile/          Expo (M0 scaffolded)
  └── API        https://kore.fly.dev/api/*  (Bearer)
web/             Consola
app/             FastAPI — transcribe/diary/memory/tasks ya existen;
                 M2 puede añadir “ingest note” unificado si hace falta
```

## Plan por fases

### M0 — Scaffold ✅
- Expo Router + tabs Día | Audio | Tareas | Misiones
- Login + SecureStore + `GET /api/me`
- iOS + Android targets en `app.json`

```bash
cd mobile && npm start
```

### M1 — Día + Tareas
- `GET /api/day`, lista tareas + complete

### M2 — Modo audio
- Grabación → `/transcribe` → ingest multi-destino (diario/memoria/tareas)
- Decidir PTT vs continuo en implementación

### M3 — Misiones
- Lista + detalle + crear/relanzar

### M4 — Pulido
- Push, Gmail corto, resumen sesión audio, EAS prod

## Open questions (quedan)

- ¿Sustituye Telegram captura o convive? (default: convive)
- ¿Push dream / misión done en M4?
