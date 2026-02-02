#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${BACKUP_FILE:?Define BACKUP_FILE con ruta al .sql}"
POSTGRES_USER="${POSTGRES_USER:-nestsecure}"
POSTGRES_DB="${POSTGRES_DB:-nestsecure_db}"

if [[ ! -f "$BACKUP_FILE" ]]; then
	echo "Backup no encontrado: $BACKUP_FILE"
	exit 1
fi

echo "==> Restaurando DB desde $BACKUP_FILE"
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_FILE"
echo "==> Restore completado"
