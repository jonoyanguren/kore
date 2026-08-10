# Spike — Crear huecos en Google Calendar desde chat

> Estado: **shipped** (2026-08-10) — chat → `propose_calendar_block` → card editable → `POST /api/calendar/events`.

## Objetivo

Desde chat: “bloquea 90 min mañana por la mañana para foco” → Jone propone un
evento → Jon confirma → se crea en el calendario **primary**.

## Qué hace falta

| Pieza | Notas |
|-------|--------|
| Scope OAuth | `calendar.readonly` + **`calendar.events`**. Requiere **Reconectar** una vez. |
| API | `POST /api/calendar/events` → Google `calendars/primary/events` |
| Confirmación | Card en chat: título/horas editables → Crear / Cancelar |
| Tool chat | Solo `propose_calendar_block` (no crea sola) |
| Conflictos | Advisory en la propuesta (`list_events` en la ventana) |

## Flujo (v1)

1. Jon en chat: “reserva mañana 10–11 foco Kore”
2. Modelo llama `propose_calendar_block`
3. Consola muestra card “Crear en Calendar?” [Crear] [Cancelar]
4. Al Crear → API write → toast + refresca Día

## No en v1

- Invitar attendees / Meet links
- Multi-calendario
- Recurrencia
- Mover/borrar eventos existentes
- Confirmación desde Telegram
