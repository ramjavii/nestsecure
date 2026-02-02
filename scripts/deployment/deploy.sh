#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> Desplegando NESTSECURE"
docker compose pull
docker compose up -d --remove-orphans

echo "==> Ejecutando migraciones"
docker compose exec -T api alembic upgrade head

echo "==> Estado de servicios"
docker compose ps
