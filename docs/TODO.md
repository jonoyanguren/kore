# Kore — TODO

Backlog **abierto**. Histórico: [`milestones.md`](./milestones.md) · Plan: [`PLAN.md`](./PLAN.md)
Piloto / cobrar: [`spikes/paid-pilot.md`](./spikes/paid-pilot.md)

Cerrar ítem → quitarlo de aquí; hito gordo → línea en `milestones.md`.

## Cómo priorizar

| Carril | Qué es | Deploy |
|--------|--------|--------|
| **Producto** | Lo que Jon vive en la consola: Día, chat, misiones, Gmail, UI | Sí — ship a Fly |
| **Plataforma** | App móvil Kore, ops | Paralelo; web sigue usable |

---

## Ahora — fase: cerrar el piloto

Spike: [`paid-pilot.md`](./spikes/paid-pilot.md)

1. [x] **Allowlist** — solo emails invitados pueden crear cuenta.
2. [x] **Landing** — “Pide acceso” en vez de registro abierto.
3. [x] **Flag en cuenta** — `allowed` (y columna `paid_until` para Stripe). Login/sesión cortan si `allowed=0`. `make account-off/on`.
4. [x] **Gasto por home** — sumar `llm_spend` del mes (Madrid) por SQLite.
5. [x] **Tope LLM** — `PILOT_LLM_CAP_USD` (default 0.5; 0 = sin corte). Corta chat, misiones, dream, Gmail draft.
6. [x] **Chip en Más** — “te queda X de Y este mes”.
7. [x] **Stripe** — Checkout + webhook. Planes 5 / 10 / 20 €. Sin keys = sin paywall.
8. [ ] **Página legal** — datos Gmail, quién eres, cómo borrar (export ya existe).

### No es del piloto

Notify misión, `/entrevista`, PDF, cola, app, logo, layout 1.6, Telegram multi, misión→tareas.

---

## Producto (después del piloto)

- [ ] Dogfood Calendar Día: **Abrir / Tarea / Prep**
- [ ] **`/entrevista` en uso** — huecos vault/memoria
- [ ] **Notify misión hecha** — toast / Telegram opcional
- [ ] **PDF / docs** en chat o Día
- [ ] **Cola de misiones** — >1 en cola (sigue max 1 running por home)

### Fino

- [ ] Logo Kore
- [ ] Ledger LLM: kinds gmail/transcribe + export CSV

### Parking

- Triage Gmail auto · compose frío · digest IA en Día
- Ampliar investing / Slow / Datafine (solo cuenta legacy)
- Multi-modelo · autorrelleno tareas · push nativo
- Calendar 2 vías (mover/borrar) — create ya en D25
- **Misión → tareas** (aparcado 2026-08-28)

### Fuera de Kore

- Programar / git desde el móvil → **proyecto aparte**

---

## Hecho (ago 2026)

- Cuentas aisladas · landing · consola = landing · tono del usuario (D30)
- Calendar read/write · dream fiable · Misiones (modos, intake, memoria, Preguntar)
- Board quieto · imágenes misión (proxy)

---

## Plataforma

- [x] Expo M0 + contenido (Día · Captura · Tareas · Misiones)
- [x] PWA de la consola
- [ ] App M2 audio / crear misión / pulido — [`spikes/mobile-app.md`](./spikes/mobile-app.md)
- [ ] Hardening ops *(solo si duele)*
