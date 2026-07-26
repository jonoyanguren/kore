#!/usr/bin/env bash
# Humo HTTP contra Kore local. Requiere:
#   1) uvicorn en 127.0.0.1:8000
#   2) .env con secretos Telegram + chat_id
# Envía mensajes reales a tu Telegram (usa el bot token del .env).
set -euo pipefail
cd "$(dirname "$0")/.."

BASE="${QA_BASE_URL:-http://127.0.0.1:8000}"

set -a
# shellcheck disable=SC1091
source .env
set +a

for var in TELEGRAM_BOT_TOKEN TELEGRAM_WEBHOOK_SECRET TELEGRAM_WEBHOOK_PATH_SECRET TELEGRAM_ALLOWED_CHAT_ID; do
  if [ -z "${!var:-}" ]; then
    echo "Falta $var en .env" >&2
    exit 1
  fi
done

WEBHOOK="${BASE}/telegram/webhook/${TELEGRAM_WEBHOOK_PATH_SECRET}"
PASS=0
FAIL=0

ok() { echo "  OK  $*"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "== QA local → ${BASE}"

# A2.1 healthz
body="$(curl -sS "${BASE}/healthz")"
if echo "$body" | grep -q '"status":"ok"'; then ok "healthz"; else bad "healthz: $body"; fi

# A2.2 forbidden without secret
code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$WEBHOOK" \
  -H 'Content-Type: application/json' \
  -d '{"update_id":1}')"
if [ "$code" = "403" ]; then ok "webhook sin secret → 403"; else bad "webhook sin secret → $code"; fi

# A2.3 bad path
code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "${BASE}/telegram/webhook/not-the-secret" \
  -H "X-Telegram-Bot-Api-Secret-Token: ${TELEGRAM_WEBHOOK_SECRET}" \
  -H 'Content-Type: application/json' \
  -d '{"update_id":1}')"
if [ "$code" = "404" ]; then ok "webhook path malo → 404"; else bad "webhook path malo → $code"; fi

post_update() {
  local payload="$1"
  curl -sS -X POST "$WEBHOOK" \
    -H "X-Telegram-Bot-Api-Secret-Token: ${TELEGRAM_WEBHOOK_SECRET}" \
    -H "Content-Type: application/json" \
    -d "$payload"
}

UID_BASE=$(( (RANDOM % 100000) + 700000 ))

# A2.4 text ping
resp="$(post_update "{
  \"update_id\": ${UID_BASE},
  \"message\": {
    \"message_id\": ${UID_BASE},
    \"chat\": {\"id\": ${TELEGRAM_ALLOWED_CHAT_ID}},
    \"from\": {\"id\": ${TELEGRAM_ALLOWED_CHAT_ID}, \"is_bot\": false, \"first_name\": \"Jon\"},
    \"text\": \"[QA] di solo: local ok\"
  }
}")"
if echo "$resp" | grep -q '"ok":true'; then ok "texto → ok (mira Telegram)"; else bad "texto → $resp"; fi

# A2.5 /hora via webhook (fast path, no LLM)
resp="$(post_update "{
  \"update_id\": $((UID_BASE + 1)),
  \"message\": {
    \"message_id\": $((UID_BASE + 1)),
    \"chat\": {\"id\": ${TELEGRAM_ALLOWED_CHAT_ID}},
    \"from\": {\"id\": ${TELEGRAM_ALLOWED_CHAT_ID}, \"is_bot\": false, \"first_name\": \"Jon\"},
    \"text\": \"/hora\"
  }
}")"
if echo "$resp" | grep -q '"ok":true'; then ok "/hora → ok (mira Telegram: fecha ES)"; else bad "/hora → $resp"; fi

# A2.6 photo + caption in same update (1x1 jpeg)
# Minimal valid JPEG
B64="/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAGcP//EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAQUCf//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQMBAT8Bf//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQIBAT8Bf//Z"
# Telegram needs a real file_id for download — we cannot fake getFile locally without mocking.
# So photo vision is MANUAL (section B3). Here we only document skip.
ok "foto+caption: MANUAL (B3) — Telegram getFile no se puede fakear sin file_id real"

echo
echo "Resultado: ${PASS} OK, ${FAIL} FAIL"
echo "Revisa Telegram para las respuestas de texto y /hora."
echo "Plan completo: docs/QA.md"
[ "$FAIL" -eq 0 ]
