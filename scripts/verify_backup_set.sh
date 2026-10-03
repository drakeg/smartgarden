#!/bin/sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <database.dump> <media.tar.gz>" >&2
  exit 2
fi

db_backup="$1"
media_backup="$2"

for path in "$db_backup" "$media_backup"; do
  if [ ! -s "$path" ]; then
    echo "Backup artifact is missing or empty: $path" >&2
    exit 1
  fi
done

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db   pg_restore --list < "$db_backup" > /dev/null

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run   --rm --no-deps --entrypoint tar web   -tzf - < "$media_backup" > /dev/null

echo "Backup set verified:"
echo "  database: $db_backup"
echo "  media:    $media_backup"
