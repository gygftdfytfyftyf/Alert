#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Настройка Telegram Tag Bot ==="
echo

if [[ ! -d .venv ]]; then
  echo "Создаю виртуальное окружение..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

if ! grep -q '^BOT_TOKEN=.\+' .env 2>/dev/null || grep -q 'your_telegram_bot_token_here' .env; then
  echo "Нужен токен бота от @BotFather."
  echo
  echo "1. Откройте https://t.me/BotFather"
  echo "2. /newbot → придумайте имя и username"
  echo "3. Скопируйте токен"
  echo
  read -r -p "Вставьте BOT_TOKEN: " token
  if [[ -z "${token}" ]]; then
    echo "Токен не введён. Заполните .env вручную."
    exit 1
  fi
  sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=${token}|" .env
  echo "Токен сохранён в .env"
  echo
  echo "В @BotFather также выполните:"
  echo "  /setprivacy → выберите бота → Disable"
  echo
fi

python3 scripts/check_token.py
