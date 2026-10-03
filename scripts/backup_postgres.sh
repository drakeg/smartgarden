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
timestamp="${BACKUP_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
backup_path="$BACKUP_DIR/smartgarden-$timestamp.dump"
tmp_path="$backup_path.tmp"

cleanup() {
  rm -f "$tmp_path"
}
trap cleanup EXIT HUP INT TERM

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db sh -c '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  exec pg_dump     --format=custom     --no-owner     --no-privileges     --username="$POSTGRES_USER"     --dbname="$POSTGRES_DB"
' > "$tmp_path"

if [ ! -s "$tmp_path" ]; then
  echo "Backup failed: dump is empty." >&2
  exit 1
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db   pg_restore --list < "$tmp_path" > /dev/null

mv "$tmp_path" "$backup_path"
trap - EXIT HUP INT TERM

echo "$backup_path"
