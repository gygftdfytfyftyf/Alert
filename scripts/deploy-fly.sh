#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export PATH="${HOME}/.fly/bin:${PATH}"

if ! command -v flyctl >/dev/null 2>&1; then
  echo "Устанавливаю flyctl..."
  curl -sSL https://fly.io/install.sh | sh
  export PATH="${HOME}/.fly/bin:${PATH}"
fi

if [[ ! -f .env ]]; then
  echo "Нет .env. Скопируйте .env.example и укажите BOT_TOKEN."
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

if [[ -z "${BOT_TOKEN:-}" ]]; then
  echo "BOT_TOKEN не задан в .env"
  exit 1
fi

APP_NAME="${FLY_APP_NAME:-aya-teg-bot}"
REGION="${FLY_REGION:-ams}"
VOLUME_NAME="${FLY_VOLUME_NAME:-bot_data}"

if ! flyctl auth whoami >/dev/null 2>&1; then
  echo "Сначала войдите: flyctl auth login"
  exit 1
fi

if ! flyctl apps list 2>/dev/null | rg -q "${APP_NAME}"; then
  echo "Создаю приложение ${APP_NAME}..."
  flyctl apps create "${APP_NAME}"
fi

if ! flyctl volumes list -a "${APP_NAME}" 2>/dev/null | rg -q "${VOLUME_NAME}"; then
  echo "Создаю volume ${VOLUME_NAME} в регионе ${REGION}..."
  flyctl volumes create "${VOLUME_NAME}" --region "${REGION}" --size 1 -a "${APP_NAME}" --yes
fi

echo "Обновляю секреты..."
flyctl secrets set \
  BOT_TOKEN="${BOT_TOKEN}" \
  BOT_OWNER_IDS="${BOT_OWNER_IDS:-}" \
  -a "${APP_NAME}"

echo "Деплой..."
flyctl deploy -a "${APP_NAME}" --remote-only

echo
echo "Готово. Логи: flyctl logs -a ${APP_NAME}"
