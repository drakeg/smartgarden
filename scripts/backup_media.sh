#!/bin/sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"
BACKUP_DIR="${BACKUP_DIR:-backups}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_path="$BACKUP_DIR/smartgarden-media-$timestamp.tar.gz"
tmp_path="$backup_path.tmp"

cleanup() {
  rm -f "$tmp_path"
}
trap cleanup EXIT HUP INT TERM

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run   --rm --no-deps --entrypoint tar web   -C /app/media -czf - . > "$tmp_path"

if [ ! -s "$tmp_path" ]; then
  echo "Media backup failed: archive is empty." >&2
  exit 1
fi

mv "$tmp_path" "$backup_path"
trap - EXIT HUP INT TERM

echo "$backup_path"
