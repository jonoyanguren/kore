# Kore — TODO

Backlog **abierto**. Histórico: [`milestones.md`](./milestones.md) · Plan: [`PLAN.md`](./PLAN.md)

Cerrar ítem → quitarlo de aquí; hito gordo → línea en `milestones.md`.

## Cómo priorizar

| Carril | Qué es | Dogfood / deploy |
|--------|--------|------------------|
| **Producto** | Lo que Jon vive en la consola: respuestas, misiones, Gmail, UI, fricciones | Sí — ship a Fly |
| **Plataforma** | Base / nuevos canales: app móvil, servidor, CI, clientes | Puede ir en paralelo; web sigue usable |

Dogfood primero → fricciones a **Producto**. Sin fricción clara ni diseño listo → se puede meter un slice de **Plataforma**.

---

## Ahora

- [ ] **Dogfood Misiones** (Jon) — Normal/Pro, imágenes, gasto; fricciones ↓ Producto
- [ ] **Dogfood Gmail reply** — Resp. → editar → Enviar; anotar tono / OAuth

---

## Producto

Cambia el uso diario en Fly.

### Abierto

- [ ] Fricciones del dogfood de Misiones *(sacar de uso real)*
- [ ] **Logo Kore** — icono/marca (web, PWA, Expo)
- [ ] **Rediseño UI** — diseñadora en curso; luego **maquetar** en consola (1.6)
- [ ] Ledger LLM: kinds gmail/transcribe + export CSV (fino)
- [ ] Git / código con confirmación (Phase 4)
- [ ] Calendar / PDF / … (Phase 5+)

### Misiones — build cerrado

Form + aclaración · plan → tareas · handoff · calidad Normal (Flash) / Pro · imágenes md · Relanzar · layout 4º.

Defaults v1: 2–6 tareas · DeepSeek por calidad · max 1 activa.

### Parking (producto)

- Perfil de tono “suena a Jon” desde sent mail (reply)
- Triage Gmail auto → labels/carpetas
- Compose frío (mail nuevo sin reply)
- Multi-cuenta / digest IA en Día
- Ampliar investing / Slow Project–Andrea / Datafine About
- Agresividad de captura
- Multi-modelo (imagen / code)
- Autorrelleno tareas en chat (sale del dogfood)

---

## Plataforma

No bloquea el dogfood web; se puede avanzar sin “romper” el día a día.

### Abierto

- [x] **M0 scaffold Expo** — `mobile/` login + tabs (Día/Audio/Tareas/Misiones)
- [x] **Móvil contenido** — Día · Captura (notas/chat) · Tareas · Misiones
- [ ] **App móvil** — M2 audio voz · crear misión · pulido · [`docs/spikes/mobile-app.md`](./spikes/mobile-app.md)
- [ ] Hardening servidor / ops *(cuando haga falta; no inventar trabajo)*

### Hecho / no cuenta como app

- [x] PWA install de la consola (atajo) · [`docs/spikes/mobile-pwa.md`](./spikes/mobile-pwa.md) — **no** es el producto móvil

### Parking (plataforma)

- Clientes / canales extra más allá de web + Telegram captura
- CI / DX gordo (si duele el ship diario)
- Offline-first / push nativo
- Capacitor wrapper (solo si algún día quisiéramos web embebida)
