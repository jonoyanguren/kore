# Kore — compañero personal (habla como Jone)

Proyecto: **Kore**. Nombre en el chat: **Jone** (editable con `ASSISTANT_NAME`).

Bot de Telegram que reenvía tus mensajes a un modelo LLM (vía OpenRouter) y te
devuelve la respuesta. El modelo puede usar herramientas para consultar datos
reales en vez de inventar: estadísticas de League of Legends (OP.GG) y
gestión de tareas de ClickUp. Roadmap del companion: ver `docs/companion-plan.md`.

## Arquitectura

```
Telegram --webhook (HTTPS)--> Fly.io (TLS automático) --> FastAPI (app) --> OpenRouter --> modelo
                                                                                 │
                                                                                 ├─ tools LoL --> MCP de OP.GG (mcp-api.op.gg)
                                                                                 └─ tools ClickUp --> API REST de ClickUp
```

- **Canal**: Telegram Bot API vía webhook.
- **Backend**: FastAPI + Python 3.12, gestionado con `uv`.
- **Modelo**: vía **OpenRouter** — diario `OPENROUTER_MODEL`
  (`deepseek/deepseek-v4-pro`); asks gordas `OPENROUTER_MODEL_STRONG`
  (`anthropic/claude-sonnet-4.6`). Alt: Opus / MiMo multimodal.
  Sin streaming — las respuestas son mensajes
  de chat cortos, no documentos largos.
- **Tool use**: `LLMAssistant` corre un loop de llamada→tool_calls→resultado
  hasta que el modelo da una respuesta final (máx. 6 iteraciones, para no
  quedar en bucle). Las tools de LoL son un *proxy transparente* hacia el
  servidor MCP oficial de OP.GG (se descargan sus schemas al arrancar, sin
  necesidad de mantenerlos a mano); las de ClickUp están definidas a mano
  sobre su API REST.
- **LoL**: servidor MCP público de OP.GG (`mcp-api.op.gg`) — sin API key, sin
  scraping, sin caducidad. Solo se exponen las tools con prefijo `lol_`
  (el servidor también tiene TFT y Valorant, que no se pidieron).
- **ClickUp**: API REST v2 con token personal (no caduca). Acceso completo —
  listar workspaces/spaces/lists, listar/crear/actualizar/cerrar tareas.
- **Despliegue**: Fly.io (app `kore`, región `fra`, 1 máquina
  `shared-cpu-1x`/256MB siempre encendida — `min_machines_running = 1` para
  evitar cold start en el webhook). TLS y certificado son automáticos, sin
  Caddy ni dominio propio: la app vive en `kore.fly.dev`.
- **Seguridad del webhook**: verificación del header
  `X-Telegram-Bot-Api-Secret-Token` (el gate real) + segmento aleatorio en la
  URL (defensa en profundidad) + whitelist de un único `chat_id`.

**Nota de seguridad**: dar acceso de código/git/deploy al bot (leer y
modificar tus repos, desplegar) queda deliberadamente fuera de esta fase —
es la pieza de mayor riesgo del roadmap (comandos disparados desde un chat de
móvil, sin la UI de confirmación que tienes en Claude Code) y se diseña
aparte, con lista blanca de repos/comandos y confirmación obligatoria antes
de cualquier acción irreversible.

## Requisitos previos

1. **Bot de Telegram**: crea uno con [@BotFather](https://t.me/BotFather),
   guarda el token.
2. **Tu `chat_id`**: escríbele al bot una vez (aunque todavía no responda) y
   después consulta `https://api.telegram.org/bot<TOKEN>/getUpdates` — ahí
   verás tu `chat.id`.
3. **API key de OpenRouter**: desde [openrouter.ai](https://openrouter.ai) →
   *Keys*. Funciona con saldo prepago.
4. **Cuenta de Fly.io** con `flyctl` instalado y autenticado
   (`flyctl auth login`, requiere terminal interactiva).
5. **Token personal de ClickUp**: Ajustes → Apps → API Token → Generate. No
   caduca.

## Setup local (antes de desplegar)

```bash
uv sync
cp .env.example .env
# completa TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_CHAT_ID, OPENROUTER_API_KEY,
# CLICKUP_API_TOKEN
# genera los dos secretos con:
openssl rand -hex 32   # -> TELEGRAM_WEBHOOK_SECRET
openssl rand -hex 32   # -> TELEGRAM_WEBHOOK_PATH_SECRET
```

Levanta API + consola web (Vite):

```bash
make start
# API  http://127.0.0.1:8000
# UI   http://127.0.0.1:5173
# Ctrl+C para ambos · make stop si quedó algo colgado
```

Solo backend: `make back` · solo front: `make front`.

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

## Despliegue en Fly.io

La app ya está creada (`fly launch`, región `fra`). Para desplegar:

```bash
# cargar los secrets (una vez, o cuando cambien)
fly secrets set \
  TELEGRAM_BOT_TOKEN=... \
  TELEGRAM_WEBHOOK_SECRET=... \
  TELEGRAM_WEBHOOK_PATH_SECRET=... \
  TELEGRAM_ALLOWED_CHAT_ID=... \
  OPENROUTER_API_KEY=... \
  CLICKUP_API_TOKEN=...

fly deploy
fly logs                  # confirmar que arrancó sin errores
./scripts/set_webhook.sh  # registra el webhook y muestra getWebhookInfo
```

Verifica el registro manualmente si quieres:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

Confirma `url` correcta, `pending_update_count: 0` y sin `last_error_message`.

Después, mándale un mensaje real al bot desde Telegram y mira `fly logs`.

## Estructura

```
app/
├── main.py                      # FastAPI, endpoint webhook, healthz, wiring de tools
├── config.py                     # variables de entorno (pydantic-settings)
├── telegram/
│   ├── schemas.py                # modelos mínimos de Update/Message de Telegram
│   └── client.py                  # sendMessage (con split de mensajes largos), setWebhook
├── llm/
│   └── llm_assistant.py           # loop de tool use + manejo de errores
├── integrations/
│   ├── lol/
│   │   └── opgg_client.py         # cliente MCP hacia mcp-api.op.gg (proxy transparente)
│   └── clickup/
│       ├── clickup_client.py      # wrapper REST puro sobre la API de ClickUp
│       └── tools.py                # schemas + handlers de tool-calling para ClickUp
└── storage/                        # vacío — memoria de conversación, RAG (SQLite)
```

## Fuera de alcance por ahora

Memoria de conversación entre mensajes, ejecución de comandos/código/git
(riesgo alto, se diseña aparte), cola de mensajes, logging estructurado,
deduplicación persistente de `update_id`, registro automático del webhook al
arrancar, Docker multi-stage, escapado de Markdown para Telegram (el bot
responde en texto plano a propósito).
