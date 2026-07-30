# Kore mobile (Expo)

Carril **Plataforma**. iOS + Android. Plan: [`docs/spikes/mobile-app.md`](../docs/spikes/mobile-app.md)

## Run

```bash
cd mobile
npm start          # Expo Go / dev client
npm run ios
npm run android
```

API por defecto: `https://kore.fly.dev`  
Override: `EXPO_PUBLIC_API_URL=http://127.0.0.1:8000`

Login = mismo `CONSOLE_SECRET` que la consola web (Bearer → SecureStore).

## Tabs (M0)

| Tab | Estado |
|-----|--------|
| Día | stub → M1 |
| Audio | stub modo notas → M2 |
| Tareas | stub → M1 |
| Misiones | stub → M3 |
