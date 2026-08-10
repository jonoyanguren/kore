# Kore — TODO

Backlog **abierto**. Histórico: [`milestones.md`](./milestones.md) · Plan: [`PLAN.md`](./PLAN.md)

Cerrar ítem → quitarlo de aquí; hito gordo → línea en `milestones.md`.

## Cómo priorizar

| Carril | Qué es | Deploy |
|--------|--------|--------|
| **Producto** | Lo que Jon vive en la consola: Día, chat, misiones, Gmail, UI | Sí — ship a Fly |
| **Plataforma** | App móvil Kore, ops | Paralelo; web sigue usable |

---

## Ahora

- [ ] Dogfood: chat → **crear bloque Calendar** (directo) · 1 semana
- [x] **Dream fiable** — `/dream` en consola + reintento modelo + fallback vivo + Día no vacío
- [ ] Cuando llegue diseño: plan de maquetación UI 1.6

---

## Producto

### Candidatos (después de Calendar write)

- [ ] Dogfood Calendar Día: **Abrir / Tarea / Prep** en eventos
- [ ] **Misión → tareas** — del Resultado, 1 clic crea ítems en el board
- [ ] **Gmail tono Jon** — perfil desde sent mail (reply)
- [ ] **`/entrevista` en uso** — huecos vault/memoria (no board)
- [ ] **PDF / docs en chat o Día** — ingerir y guardar en memoria
- [ ] **Cola de misiones** — >1 en cola (sigue max 1 running)
- [ ] **Notify misión hecha** — toast / Telegram opcional

### Abierto (fino / no urgente)

- [ ] **Logo Kore** — icono/marca (web, PWA, Expo)
- [ ] **Rediseño UI** — diseñadora → maquetar consola (1.6)
- [ ] Ledger LLM: kinds gmail/transcribe + export CSV

### Parking (producto)

- Triage Gmail auto → labels/carpetas
- Compose frío (mail nuevo sin reply)
- Multi-cuenta / digest IA en Día
- Ampliar investing / Slow Project–Andrea / Datafine About
- Agresividad de captura
- Multi-modelo (imagen / code)
- Autorrelleno tareas en chat
- Push nativo (vía app)
- Escribir/sync 2 vías Calendar (mover/borrar, multi-cal) — create bloque ya en D25

### Fuera de Kore

- Programar / git desde el móvil → **proyecto aparte** (no mezclar con este repo)

---

## Plataforma

### Abierto

- [x] **M0 scaffold Expo** — `mobile/` login + tabs
- [x] **Móvil contenido** — Día · Captura · Tareas · Misiones
- [ ] **App móvil** — M2 audio voz · crear misión · pulido · [`docs/spikes/mobile-app.md`](./spikes/mobile-app.md)
- [ ] Hardening servidor / ops *(solo si duele)*

### Hecho / no cuenta como app

- [x] PWA install de la consola (atajo) · [`docs/spikes/mobile-pwa.md`](./spikes/mobile-pwa.md)

### Parking (plataforma)

- Clientes extra más allá de web + Telegram captura
- CI / DX gordo
- Offline-first
