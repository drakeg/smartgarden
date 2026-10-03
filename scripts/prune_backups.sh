#!/bin/sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

case "$RETENTION_DAYS" in
  ''|*[!0-9]*)
    echo "RETENTION_DAYS must be a non-negative integer." >&2
    exit 2
    ;;
esac

if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi

find_candidates() {
  find "$BACKUP_DIR" -type f \(     -name 'smartgarden-????????T??????Z.dump' -o     -name 'smartgarden-media-????????T??????Z.tar.gz'   \) -mtime "+$RETENTION_DAYS" -print
}

candidates="$(find_candidates)"

if [ -z "$candidates" ]; then
  echo "No SmartGarden backup artifacts older than $RETENTION_DAYS days."
  exit 0
fi

if [ "${PRUNE_CONFIRM:-}" != "YES" ]; then
  echo "Dry run: the following SmartGarden backup artifacts are older than $RETENTION_DAYS days:"
  printf '%s\n' "$candidates"
  echo "Set PRUNE_CONFIRM=YES to delete only these matching artifacts."
  exit 0
fi

find "$BACKUP_DIR" -type f \(   -name 'smartgarden-????????T??????Z.dump' -o   -name 'smartgarden-media-????????T??????Z.tar.gz' \) -mtime "+$RETENTION_DAYS" -exec rm -f -- {} +

echo "Pruned SmartGarden backup artifacts older than $RETENTION_DAYS days."
