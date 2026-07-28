# Kore — TODO

Backlog **abierto**. Histórico: `[milestones.md](./milestones.md)` · Plan: `[PLAN.md](./PLAN.md)`

Cerrar ítem → quitarlo de aquí; hito gordo → línea en `milestones.md`.

## TODO

- [x] Fecha bien en pantalla Board
- [x] Limpiar la UI (pasada 1: menos chrome Chat/Board/Día; chips; CSS muerto)
- [ ] UI viva — rediseño aparte (Jon)
- [x] Vista Día: una columna de lectura (no grid 3 cols)
- [x] Chrome limpio: Chat/Board sin rail; LLM/Docs/Memoria en drawer «Más»
- [x] Día sin CTAs duplicados; Board sin buscar/filtro; chips de proyecto
- [x] Toast móvil arriba (no encima del mic)

## P0 — Dogfood

- [x] Briefing en vista Día (cron / catch-up) — en uso
- [x] Operar desde consola (chat / mic / board) — dogfood continuo
- [x] Dream no debe resucitar tareas archivadas (`add_task` fuera del dream + dedupe)

Fricciones nuevas → ítems sueltos arriba o Parking.

## P1 — Phase 1.6 (producto)

- [x] **Voz one-tap** — mic → OpenRouter Whisper → input del chat
- [x] **Mobile / empty states** — bar + mic + empties
- [x] **Proyectos** — slug en tareas; el modelo infiere (sin chips de espacio)
- [x] **Privacidad** — overview, export vault zip, borrar categoría

## P2 — Phase 2 Gmail (MVP)

- [x] OAuth Google + refresh en `/data` — scope `gmail.modify`
- [x] Cliente: listar hoy/unread + marcar leído
- [x] Vista Día: bloque Inbox (lista)
- [x] `/inbox` en chat (+ skill companion)
- [x] Conectar cuenta en prod + smoke listado
- [x] Botón Inbox → tarea (IA + link mail)
- [ ] (Luego) digest en cron mañana / dream
- [ ] Triage + log de marcados leídos
- ~~Digest IA en Día~~ — aparcado (lista basta)## P2+ — Después

- [ ] Misiones background
- [ ] Git/código con confirmación
- [ ] Calendar / PDF / …

## Parking

- Triage Gmail auto → labels/carpetas
- Ampliar investing / Slow Project–Andrea / Datafine About
- Agresividad de captura
- Multi-modelo (imagen / code)
- Autorrelleno tareas en chat (sale del dogfood)

