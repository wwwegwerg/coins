#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_COMPOSE_FILE="${ROOT_DIR}/docker-compose.yml"
SEG_COMPOSE_DIR="${ROOT_DIR}/coins-obj-seg-main"

print_help() {
  cat <<'HELP'
Usage:
  ./run_services.sh [-back] [-web] [-bot]

Flags:
  -back    start backend container
  -web     start web container (automatically includes backend)
  -bot     start telegram bot container (automatically includes backend)

Examples:
  ./run_services.sh -back -bot
  ./run_services.sh -back -web
  ./run_services.sh -back -web -bot

If no flags are passed, all three are started.
HELP
}

want_back=false
want_web=false
want_bot=false

if [[ $# -eq 0 ]]; then
  want_back=true
  want_web=true
  want_bot=true
else
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -back) want_back=true ;;
      -web)  want_web=true ;;
      -bot)  want_bot=true ;;
      -h|--help)
        print_help
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        print_help
        exit 1
        ;;
    esac
    shift
  done
fi

if [[ "$want_web" == true || "$want_bot" == true ]]; then
  want_back=true
fi

ensure_container_running() {
  local name="$1"
  shift

  if docker container inspect "$name" >/dev/null 2>&1; then
    docker start "$name" >/dev/null
  else
    docker run -d --name "$name" --restart unless-stopped "$@" >/dev/null
  fi
}

echo "[1/4] Starting PostgreSQL and Redis containers..."
ensure_container_running coins_pg \
  -e POSTGRES_DB=practice \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5433:5432 \
  postgres:14

ensure_container_running coins_redis \
  -p 6379:6379 \
  redis:7-alpine

echo "[2/4] Starting local object detection+segmentation stack..."
(
  cd "$SEG_COMPOSE_DIR"
  docker compose up -d --build florence-api sam-api

  wait_for_healthy() {
    local container="$1"
    local timeout_seconds="${2:-1200}"
    local waited=0

    while true; do
      local status
      status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container" 2>/dev/null || echo unknown)"
      if [[ "$status" == "healthy" || "$status" == "running" ]]; then
        break
      fi
      if [[ "$status" == "exited" || "$status" == "dead" ]]; then
        echo "Container $container failed to start (status=$status)." >&2
        docker logs --tail 120 "$container" || true
        exit 1
      fi
      if (( waited >= timeout_seconds )); then
        echo "Timed out waiting for $container to become healthy." >&2
        docker logs --tail 120 "$container" || true
        exit 1
      fi
      sleep 5
      waited=$((waited + 5))
    done
  }

  wait_for_healthy florence-api 1800
  wait_for_healthy sam-api 1800

  docker compose up -d --build predict-api
)

echo "[3/4] Starting requested app services..."
services=()
if [[ "$want_back" == true ]]; then
  services+=(backend)
fi
if [[ "$want_web" == true ]]; then
  services+=(web)
fi
if [[ "$want_bot" == true ]]; then
  docker rm -f coin_detector_telegram_bot >/dev/null 2>&1 || true
  services+=(telegram-bot)
fi

docker compose -f "$APP_COMPOSE_FILE" up -d --build "${services[@]}"

echo "[4/4] Current status"
docker compose -f "$APP_COMPOSE_FILE" ps
(
  cd "$SEG_COMPOSE_DIR"
  docker compose ps
)

echo "Done."
HELP_TEXT=$'Useful checks:\n  curl http://127.0.0.1:8000/health\n  curl http://127.0.0.1:8010/ready\n  open http://127.0.0.1:3000'
echo "$HELP_TEXT"
