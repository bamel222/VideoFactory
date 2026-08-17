#!/bin/bash
# Backup script: PostgreSQL dump + assets tar
set -euo pipefail

BACKUP_DIR=${BACKUP_DIR:-/backups}
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Postgres dump
pg_dump "$DATABASE_URL" -Fc > "$BACKUP_DIR/db_$TS.dump"

# Assets
tar czf "$BACKUP_DIR/assets_$TS.tar.gz" /data/assets

# Rotate: keep last 14
ls -1t "$BACKUP_DIR"/db_*.dump | tail -n +15 | xargs -r rm --
ls -1t "$BACKUP_DIR"/assets_*.tar.gz | tail -n +15 | xargs -r rm --
