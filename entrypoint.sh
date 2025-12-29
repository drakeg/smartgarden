#!/bin/sh
set -e

# Migrate database, collect static, then exec passed command
# It's safe to run migrate/collectstatic repeatedly in container restarts.

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Execute the container CMD (e.g. gunicorn)
exec "$@"
