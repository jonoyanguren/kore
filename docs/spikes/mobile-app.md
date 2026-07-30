# App móvil Kore — producto (Expo)

Carril: **Plataforma**. Distinto de la consola web / PWA.

Jon = experto Expo → **stack cerrado: Expo (RN)**.

## Intención

App de **uso diario en el teléfono** con UX propia — no “la consola en chiquito”.

- Web = operar (board, misiones gordas, Gmail, Más…).
- Móvil = captura + día + tareas/misiones reconocibles.
- **Modo audio** = la superficie que no existe en web (notas sin chat).

## Superficies

| Tab / pantalla | Rol |
|----------------|-----|
| **Día** | Briefing compacto + lo de hoy |
| **Audio** | Notas de voz encadenadas, sin chat |
| **Tareas** | Lista / check ≈ web (sin board denso) |
| **Misiones** | Lista + estado + informe ≈ web |

Gmail ligero = phase 2 móvil. Rediseño desktop = paralelo Producto, no bloquea.

## Arquitectura

```
mobile/          Expo app (este repo, carpeta hermana de web/)
  └── API        https://kore.fly.dev/api/*  (Bearer CONSOLE_SECRET)
web/             Consola (sin cambios de layout compartido)
app/             FastAPI — endpoints ya listos; audio session = slice fino si hace falta
```

- Auth: **Bearer** en `SecureStore` (la consola ya acepta cookie o Bearer).
- Audio path v0: `POST /api/transcribe` → `POST /api/diary` (y/o memoria) por nota.
- Más adelante: `POST /api/audio-session` (cerrar sesión → resumen opcional) si el flujo lo pide.
- No compartir componentes UI con Vite; sí tipos/contratos API (opcional `packages/api-types` luego).

## Plan por fases

### M0 — Scaffold (½ día)
- `npx create-expo-app` en `mobile/` (Expo Router + TS).
- Tabs: Día | Audio | Tareas | Misiones (stubs).
- Login (secret → SecureStore) + `GET /api/me`.
- Dev: apunta a Fly o a local tunnel; EAS build cuando haga falta dispositivo real.

**Hecho:** abre la app, login, 4 tabs vacías.

### M1 — Día + Tareas (1–2 días)
- `GET /api/day` → pantalla Día.
- `GET/PATCH/complete` tareas → lista + check.
- Pull-to-refresh.

**Hecho:** dogfood matutino en el tren sin abrir Safari.

### M2 — Modo audio (estrella, 2–3 días)
- Pantalla sin chat: hold/tap → grabar → soltar → “guardado”.
- Cola de notas de la sesión (contador, lista mínima de clips).
- Por nota: upload audio → `/transcribe` → `/diary` (tag `audio` / sesión id).
- Al salir: opcional “sesión cerrada · N notas” (sin LLM reply en v1; resumen = M2.5).

**Hecho:** le cuentas el rollo andando; aparece en diario web.

### M3 — Misiones (1–2 días)
- Lista + detalle markdown (mismo espíritu que web).
- Crear misión simple (título/brief/calidad) + Relanzar/Cancelar.
- Sin editor de markdown fancy; WebView o markdown lite.

**Hecho:** seguir misiones desde el móvil.

### M4 — Pulido (cuando duela)
- Push (dream 09:00 / misión done) — opcional.
- Gmail reply corto.
- Resumen al cerrar sesión audio (1 call LLM).
- Icono / splash / EAS production.

## Orden recomendado

**M0 → M2 temprano** (audio es la razón de la app) → M1 en paralelo o justo antes → M3 → M4.

Si quieres validar API ya: M0+M1 primero (½–1 día) y M2 encima.

## Fuera de alcance (ahora)

- Wrapper PWA / Capacitor como producto.
- Offline-first gordo.
- Paridad total con Más / ledger / drawers.
- Sustituir Telegram el día 1 (conviven hasta que audio gane).

## Open questions (Jon)

1. ¿iOS first o iOS+Android desde M0?
2. ¿Audio: push-to-talk o grabación continua con pausas?
3. ¿Cada nota → solo diario, o también “extrae tareas” (LLM) en v1?

## Relación con dogfood web

Seguir dogfood Misiones/Gmail en web (Producto).  
Móvil = carril Plataforma en paralelo cuando digamos “dale a M0”.
