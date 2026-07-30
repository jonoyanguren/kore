# Spike — móvil (PWA) · 2026-07-30

Carril: **Plataforma**. No bloquea dogfood web.

## Pregunta

¿Basta envolver la consola actual (`kore.fly.dev`) como app instalable, o hace falta app nativa (Expo/Capacitor)?

## Corte del spike (v0)

1. Web App Manifest + iconos
2. Service worker mínimo (requisito de install en Chromium)
3. Meta iOS “Add to Home Screen”
4. Probar en el teléfono: icono → login → Día / Misiones usable

**Fuera:** offline-first, push, store, React Native, rediseño mobile-only.

## Criterio de decisión

| Resultado | Siguiente |
|-----------|-----------|
| Día + chat + misiones OK desde el home screen | Seguir en **PWA**; pulir safe-area / gestos |
| UX rota (teclado, auth cookie, layouts) | Lista fricciones → Producto o Capacitor shell |
| Necesitas cámara/notificaciones nativas ya | Valorar Capacitor / Expo (otro spike) |

## Cómo probar

1. En el móvil: Safari/Chrome → https://kore.fly.dev/
2. **iOS:** Compartir → Añadir a pantalla de inicio  
3. **Android Chrome:** menú → Instalar app / Añadir a inicio  
4. Abrir desde el icono (standalone) y anotar: login, Día, chat, misiones, teclado

Notas → `docs/TODO.md` Plataforma o fricciones Producto.
