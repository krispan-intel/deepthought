#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "docker compose (or docker-compose) not found"
  exit 1
fi

"${COMPOSE_CMD[@]}" stop deepthought-service
"${COMPOSE_CMD[@]}" rm -f deepthought-service

echo "DeepThought service stopped."
