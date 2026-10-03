#!/bin/sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"

if [ "$#" -ne 1 ]; then
  echo "Usage: RESTORE_CONFIRM=YES $0 <media-backup.tar.gz>" >&2
  exit 2
fi

archive_path="$1"

if [ "${RESTORE_CONFIRM:-}" != "YES" ]; then
  echo "Refusing restore. Set RESTORE_CONFIRM=YES to acknowledge media changes." >&2
  exit 2
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

if [ ! -s "$archive_path" ]; then
  echo "Media archive is missing or empty: $archive_path" >&2
  exit 1
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run   --rm --no-deps --entrypoint tar web   -C /app/media -xzf - < "$archive_path"

echo "Media restore completed. Existing unrelated files were left in place." >&2
