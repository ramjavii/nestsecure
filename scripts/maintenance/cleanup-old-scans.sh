#!/usr/bin/env bash
set -euo pipefail

REPORTS_DIR="${REPORTS_DIR:-./data/reports}"
DAYS="${DAYS:-30}"

if [[ ! -d "$REPORTS_DIR" ]]; then
	echo "Directorio no encontrado: $REPORTS_DIR"
	exit 0
fi

echo "==> Limpieza de reportes antiguos en $REPORTS_DIR (>$DAYS días)"
find "$REPORTS_DIR" -type f -mtime "+$DAYS" -print -delete
