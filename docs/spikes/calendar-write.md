# Spike — Crear huecos en Google Calendar desde chat

> Estado: **shipped** — `create_calendar_block` crea al momento (sin card de confirmación).

## Flujo

1. Jon: “reserva mañana 10–11 foco Kore”
2. Si está claro → una tool `create_calendar_block`
3. Si falta día/hora → 1 pregunta; sin `list_calendar` de validación previa

## No en v1

- Attendees / Meet / recurrencia / multi-cal / mover-borrar
