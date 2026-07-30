# App móvil Kore — producto (no wrapper)

Carril: **Plataforma**. Distinto de la consola web / PWA.

## Intención

App de **uso diario en el teléfono** con UX propia — no “la consola en chiquito”.

La web sigue siendo el sitio de operar (board, misiones gordas, Gmail, Más…).
El móvil prioriza captura + día + lo que se hace andando / en el sofá.

## Hipótesis de superficie (v1 a validar con Jon)

| En móvil | En web (sigue) |
|----------|----------------|
| Briefing / Día | Layouts Día + Focus + Operate + Misiones |
| Captura rápida (voz/texto/foto) | Chat completo + tools |
| Tareas del día (check / una acción) | Board rico, editor, proyectos |
| Inbox Gmail ligero (leer / reply corto) | Triage + reply editable largo |
| Estado de misiones (seguir, no diseñar) | Crear / relanzar / leer informe largo |

**Fuera de v1 móvil (salvo que digamos lo contrario):** maquetar el rediseño desktop, Git, drawers densos, ledger completo.

## Stack (propuesta, no cerrado)

1. **Expo (React Native)** — app nativa de verdad, cambios de UI significativos fáciles.
2. Mismo backend Fly (`/api/*` + cookie/Bearer).
3. Web y móvil comparten API; **no** comparten layout.

Alternativa más tarde: Capacitor solo si quisiéramos reutilizar mucho React web (choca con “cambios significativos”).

## Spike siguiente (cuando toque build)

1. Repo/app Expo mínima: login + Día (read) + lista tareas open.
2. Una captura (texto → mismo chat/API).
3. Decidir navegación (tabs: Día | Captura | Tareas).

Hasta entonces: dogfood web; diseñadora en desktop; este doc es la brújula.

## Open questions

- ¿iOS only primero o iOS+Android?
- ¿Sustituye Telegram captura o convive?
- ¿Push para dream 09:00 / misión done?
