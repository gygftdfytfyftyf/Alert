#!/usr/bin/env bash
# Деплой на любой Linux VPS (Ubuntu/Debian) с Docker.
# Запуск на сервере: bash scripts/deploy-vps.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/gygftdfytfyftyf/Alert.git}"
BRANCH="${BRANCH:-cursor/telegram-tag-bot-8d30}"
INSTALL_DIR="${INSTALL_DIR:-/opt/aya-teg-bot}"

if [[ $EUID -ne 0 ]]; then
  echo "Запустите от root: sudo bash scripts/deploy-vps.sh"
  exit 1
fi

apt-get update -qq
apt-get install -y -qq git docker.io docker-compose-plugin curl

systemctl enable --now docker

if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
  git clone --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
else
  cd "${INSTALL_DIR}"
  git fetch origin "${BRANCH}"
  git checkout "${BRANCH}"
  git pull origin "${BRANCH}"
fi

cd "${INSTALL_DIR}"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo
  echo "Отредактируйте ${INSTALL_DIR}/.env — укажите BOT_TOKEN и BOT_OWNER_IDS"
  echo "Затем снова: bash scripts/deploy-vps.sh"
  exit 0
fi

mkdir -p data
docker compose down 2>/dev/null || true
docker compose up -d --build

echo
echo "Бот запущен. Логи: docker compose -f ${INSTALL_DIR}/docker-compose.yml logs -f"
echo "Автозапуск после перезагрузки: restart: unless-stopped уже в docker-compose.yml"
