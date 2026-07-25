# jornvis — Asistente personal (Fase 1)

Bot de Telegram que reenvía tus mensajes a un modelo LLM (vía OpenRouter) y te
devuelve la respuesta. Fase 1 = esqueleto conversacional puro: sin memoria de
conversación, sin ClickUp, sin resúmenes de commits, sin RAG, sin ejecución
de comandos. Esas son fases futuras — ver `app/integrations/` y
`app/storage/`, que están vacíos a propósito.

## Arquitectura

```
Telegram --webhook (HTTPS)--> Caddy (TLS automático) --> FastAPI (app) --> OpenRouter --> modelo elegido
```

- **Canal**: Telegram Bot API vía webhook.
- **Backend**: FastAPI + Python 3.12, gestionado con `uv`.
- **Modelo**: configurable vía `OPENROUTER_MODEL` (por defecto
  `anthropic/claude-sonnet-5`), sin streaming — las respuestas son mensajes
  de chat cortos, no documentos largos.
- **Despliegue**: Docker Compose (`app` + `caddy`), Caddy es el único servicio
  expuesto a internet (80/443); `app` vive solo en la red interna de Docker.
- **Seguridad del webhook**: verificación del header
  `X-Telegram-Bot-Api-Secret-Token` (el gate real) + segmento aleatorio en la
  URL (defensa en profundidad) + whitelist de un único `chat_id`.

## Requisitos previos

1. **Bot de Telegram**: crea uno con [@BotFather](https://t.me/BotFather),
   guarda el token.
2. **Tu `chat_id`**: escríbele al bot una vez (aunque todavía no responda) y
   después consulta `https://api.telegram.org/bot<TOKEN>/getUpdates` — ahí
   verás tu `chat.id`.
3. **API key de OpenRouter**: desde [openrouter.ai](https://openrouter.ai) →
   *Keys*. Funciona con saldo prepago.
4. **Dominio o subdominio** apuntando (registro A) a la IP pública del
   servidor Hetzner — necesario para que Caddy pueda emitir el certificado
   TLS. Tiene que resolver *antes* de levantar el stack.

## Setup local (antes de desplegar)

```bash
uv sync
cp .env.example .env
# completa TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_CHAT_ID, OPENROUTER_API_KEY
# genera los dos secretos con:
openssl rand -hex 32   # -> TELEGRAM_WEBHOOK_SECRET
openssl rand -hex 32   # -> TELEGRAM_WEBHOOK_PATH_SECRET
```

Levanta el servidor local:

```bash
uv run uvicorn app.main:app --reload
```

Verifica que responde:

```bash
curl http://localhost:8000/healthz
# {"status":"ok"}
```

### Simular un mensaje de Telegram sin desplegar nada

Como el bot token y la API key son reales, esto dispara un mensaje real a tu
Telegram aunque el webhook todavía no esté registrado con Telegram — estás
llamando directamente a tu propio endpoint local:

```bash
curl -X POST "http://localhost:8000/telegram/webhook/<TELEGRAM_WEBHOOK_PATH_SECRET>" \
  -H "X-Telegram-Bot-Api-Secret-Token: <TELEGRAM_WEBHOOK_SECRET>" \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 1,
    "message": {
      "message_id": 1,
      "chat": {"id": <TELEGRAM_ALLOWED_CHAT_ID>},
      "from": {"id": <TELEGRAM_ALLOWED_CHAT_ID>, "is_bot": false},
      "text": "hola, ¿estás ahí?"
    }
  }'
```

Deberías ver `{"ok":true}` de inmediato y, unos segundos después, la
respuesta del modelo llegando a tu Telegram real. Otros casos a probar:

- Header o path incorrectos → `403` / `404`.
- `chat_id` distinto al whitelisteado → `200`, pero sin llamada al modelo
  (revisar logs).
- Mensaje sin `text` (sticker, foto) → respuesta canned de "solo leo texto".
- `/start` → saludo fijo, no pasa por el modelo.
- Texto largo (fuerza una respuesta de +4096 caracteres) → llega partido en
  varios mensajes, en orden.

## Despliegue en el Hetzner

```bash
# en el servidor, con el repo copiado y .env completo (con DOMAIN y ACME_EMAIL)
docker compose up -d --build
docker compose logs -f caddy   # confirmar que emite el certificado sin errores
./scripts/set_webhook.sh       # registra el webhook y muestra getWebhookInfo
```

Verifica el registro manualmente si quieres:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

Confirma `url` correcta, `pending_update_count: 0` y sin `last_error_message`.

Después, mándale un mensaje real al bot desde Telegram y mira
`docker compose logs -f app`.

## Estructura

```
app/
├── main.py               # FastAPI, endpoint webhook, healthz
├── config.py              # variables de entorno (pydantic-settings)
├── telegram/
│   ├── schemas.py         # modelos mínimos de Update/Message de Telegram
│   └── client.py           # sendMessage (con split de mensajes largos), setWebhook
├── llm/
│   └── llm_assistant.py    # llamada a OpenRouter + manejo de errores
├── integrations/            # vacío — Fase 2+: ClickUp, resúmenes de commits
└── storage/                  # vacío — Fase 2+: memoria de conversación, RAG (SQLite)
```

## Fuera de alcance en esta fase

Cola de mensajes, logging estructurado, deduplicación persistente de
`update_id`, registro automático del webhook al arrancar, Docker multi-stage,
escapado de Markdown para Telegram (el bot responde en texto plano a
propósito). Ver el historial de la sesión de diseño si quieres el
razonamiento completo detrás de cada decisión.
