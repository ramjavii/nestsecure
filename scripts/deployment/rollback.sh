#!/usr/bin/env bash
set -euo pipefail

ROLLBACK_REF="${ROLLBACK_REF:?Define ROLLBACK_REF (tag/commit) para rollback}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> Rollback a ${ROLLBACK_REF}"
git fetch --all --tags
git checkout "$ROLLBACK_REF"

echo "==> Rebuild y restart"
docker compose build
docker compose up -d --remove-orphans

echo "==> Estado de servicios"
docker compose ps
