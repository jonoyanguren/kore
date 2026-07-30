# Kore mobile (Expo)

Carril **Plataforma**. iOS + Android. Plan: [`docs/spikes/mobile-app.md`](../docs/spikes/mobile-app.md)

**SDK 54** (compatible con Expo Go de la App Store). SDK 57 aún no está en el Expo Go de iOS.

## Run

```bash
cd mobile
npm start
```

En el iPhone: abre **Expo Go** → escanea el QR (misma Wi‑Fi).  
Si no carga: en la terminal pulsa `s` no; mejor `shift+r` o reinicia con:

```bash
npx expo start --clear
```

API por defecto: `https://kore.fly.dev`  
Override: `EXPO_PUBLIC_API_URL=http://127.0.0.1:8000`

Login = mismo `CONSOLE_SECRET` que la consola web.

## Tabs (M0)

| Tab | Estado |
|-----|--------|
| Día | stub → M1 |
| Audio | stub modo notas → M2 |
| Tareas | stub → M1 |
| Misiones | stub → M3 |
