#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "Сначала выполните: bash scripts/setup.sh"
  exit 1
fi

# shellcheck disable=SC1091
if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

mkdir -p data
exec python3 -m bot.main
