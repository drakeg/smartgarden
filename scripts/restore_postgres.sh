#!/bin/sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"

if [ "$#" -ne 1 ]; then
  echo "Usage: RESTORE_CONFIRM=YES $0 <backup.dump>" >&2
  exit 2
fi

backup_path="$1"

if [ "${RESTORE_CONFIRM:-}" != "YES" ]; then
  echo "Refusing restore. Set RESTORE_CONFIRM=YES to acknowledge destructive replacement." >&2
  exit 2
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

if [ ! -s "$backup_path" ]; then
  echo "Backup file is missing or empty: $backup_path" >&2
  exit 1
fi

echo "Restoring $backup_path into the configured production database..." >&2
echo "Stop application writers before continuing with a production restore." >&2

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db sh -c '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  exec pg_restore     --clean     --if-exists     --no-owner     --no-privileges     --exit-on-error     --username="$POSTGRES_USER"     --dbname="$POSTGRES_DB"
' < "$backup_path"

echo "Restore completed." >&2
