#!/usr/bin/env bash
# One-time (or rare) registration of the Telegram webhook.
# Run this after `fly deploy` — not automatically at app startup.
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
source .env
set +a

for var in TELEGRAM_BOT_TOKEN DOMAIN TELEGRAM_WEBHOOK_PATH_SECRET TELEGRAM_WEBHOOK_SECRET; do
  if [ -z "${!var:-}" ]; then
    echo "Falta $var en .env" >&2
    exit 1
  fi
done

WEBHOOK_URL="https://${DOMAIN}/telegram/webhook/${TELEGRAM_WEBHOOK_PATH_SECRET}"

echo "Registrando webhook: ${WEBHOOK_URL}"

curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=${WEBHOOK_URL}" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}"

echo
echo "Verificando registro:"
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
echo
