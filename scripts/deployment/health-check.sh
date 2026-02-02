#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "==> Health check API: ${BASE_URL}/health"
curl -fsS "${BASE_URL}/health" > /dev/null

echo "==> Estado de contenedores"
docker compose ps
