#!/bin/sh
set -eu

timestamp="${BACKUP_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
export BACKUP_TIMESTAMP="$timestamp"

db_backup="$(sh scripts/backup_postgres.sh)"
media_backup="$(sh scripts/backup_media.sh)"

sh scripts/verify_backup_set.sh "$db_backup" "$media_backup"

printf '%s\n' "Database: $db_backup" "Media: $media_backup"
