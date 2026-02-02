#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
POSTGRES_USER="${POSTGRES_USER:-nestsecure}"
POSTGRES_DB="${POSTGRES_DB:-nestsecure_db}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/nestsecure_${POSTGRES_DB}_${STAMP}.sql"

echo "==> Backup DB a $BACKUP_FILE"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE"
echo "==> Backup completado"
