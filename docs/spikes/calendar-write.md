# Spike — Crear huecos en Google Calendar desde chat

> Estado: **investigación** (no shipped). Read-only Calendar ya está (D24).
> Companion actions Día: Abrir / Tarea / Prep (2026-08-10).

## Objetivo

Desde chat: “bloquea 90 min mañana por la mañana para foco” → Jone propone un
evento → Jon confirma → se crea en el calendario **primary**.

## Qué hace falta

| Pieza | Notas |
|-------|--------|
| Scope OAuth | Hoy solo `calendar.readonly`. Hace falta **write**: `https://www.googleapis.com/auth/calendar.events` (o `calendar`). Requiere **Reconectar** una vez. |
| API | `POST .../calendars/primary/events` con `summary`, `start`, `end`, `timeZone=Europe/Madrid` |
| Confirmación | Igual espíritu que Gmail reply: borrador editable → confirmar. No crear a ciegas. |
| Tool chat | `propose_calendar_block` (solo propone) + acción UI/confirm, **o** tool `create_calendar_event` gated por flag de confirmación en consola. |
| Conflictos | Antes de crear: `list_events` en la ventana; avisar si pisa algo. |

## Flujo propuesto (v1)

1. Jon en chat: “reserva mañana 10–11 foco Kore”
2. Modelo llama tool de **propuesta** → `{title, starts_at, ends_at, reason}`
3. Consola muestra card “Crear en Calendar?” [Editar] [Crear] [Cancelar]
4. Al Crear → API write → toast + refresca Día

## No en v1

- Invitar attendees / Meet links
- Multi-calendario
- Recurrencia
- Mover/borrar eventos existentes (sí más adelante con confirmación)

## Decisión pendiente

- ¿Scope mínimo `calendar.events` (recomendado) o full `calendar`?
- ¿Confirmación solo en consola web, o también Telegram inline keyboard?
