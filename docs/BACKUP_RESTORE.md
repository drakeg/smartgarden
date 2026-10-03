# Production Backup and Restore

Smart Garden production data has two independent durable components:

- PostgreSQL data, stored in the `pgdata` Docker volume.
- Uploaded pod-note photos, stored in the `mediafiles` Docker volume.

A complete recovery point requires both artifacts from roughly the same time.

## Create backups

From the repository root with a valid `.env.prod`, create a coordinated backup set:

```bash
sh scripts/backup_all.sh
```

The wrapper gives the database dump and media archive the same UTC timestamp and verifies both formats before reporting success. You can still run the component scripts individually:

```bash
sh scripts/backup_postgres.sh
sh scripts/backup_media.sh
```

Both scripts write timestamped files under `backups/` by default. Override the destination when backups should land on a mounted/off-host path:

```bash
BACKUP_DIR=/mnt/backups/smartgarden sh scripts/backup_postgres.sh
BACKUP_DIR=/mnt/backups/smartgarden sh scripts/backup_media.sh
```

The PostgreSQL script uses `pg_dump --format=custom`, which supports validation/listing with `pg_restore --list` and flexible restore behavior. Output is first written to a temporary file and renamed only after a non-empty dump is produced.

The media script archives the persistent `/app/media` volume as a gzip-compressed tar archive and also uses an atomic temporary-file write.

Generated `backups/`, `*.dump`, and archives should be copied to storage outside the Docker host. A local Docker volume or local backup directory alone does not protect against host loss.

## Restore PostgreSQL

A database restore replaces existing database objects. Schedule a maintenance window and stop application writers first:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml stop nginx web celery-worker
RESTORE_CONFIRM=YES sh scripts/restore_postgres.sh backups/smartgarden-YYYYMMDDTHHMMSSZ.dump
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d web nginx
```

If the async-email profile is normally enabled, start it again with the same profile after the restore.

The restore script uses `pg_restore --clean --if-exists --exit-on-error --no-owner --no-privileges`. It refuses to run unless `RESTORE_CONFIRM=YES` is supplied.

## Restore uploaded media

Media restore overlays files from the archive into the persistent media volume. It does not delete unrelated files already present:

```bash
RESTORE_CONFIRM=YES sh scripts/restore_media.sh backups/smartgarden-media-YYYYMMDDTHHMMSSZ.tar.gz
```

Restore the database and media artifacts from the same recovery point whenever possible so database photo references match the files on disk.

## Verify an existing backup set

You can re-check existing artifacts without restoring them:

```bash
sh scripts/verify_backup_set.sh \
  backups/smartgarden-YYYYMMDDTHHMMSSZ.dump \
  backups/smartgarden-media-YYYYMMDDTHHMMSSZ.tar.gz
```

The command asks PostgreSQL's `pg_restore --list` to parse the DB dump and asks `tar` inside the application image to list the media archive. It does not modify the database or media volume.

## Local retention

The retention helper defaults to a 30-day **dry run** and only matches SmartGarden's timestamped DB/media backup filenames:

```bash
sh scripts/prune_backups.sh
```

Choose another age with `RETENTION_DAYS`:

```bash
RETENTION_DAYS=14 sh scripts/prune_backups.sh
```

Only after reviewing the dry-run list should deletion be enabled:

```bash
RETENTION_DAYS=30 PRUNE_CONFIRM=YES sh scripts/prune_backups.sh
```

This is local retention only. Keep independent off-host copies according to your recovery requirements.

## Verification after restore

After recovery:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
curl -f http://localhost:${APP_PORT:-80}/health/
curl -f http://localhost:${APP_PORT:-80}/ready/
```

Then sign in and verify at least one garden, pod note, and uploaded photo from before the recovery point.

## Operational guidance

Choose a retention policy appropriate to the deployment and copy backups off-host. Periodically test restores in a non-production environment; a backup is not proven usable until it has been restored successfully.
