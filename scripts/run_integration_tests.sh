#!/usr/bin/env bash
# ============================================================================
# Local equivalent of .github/workflows/ci.yml
# Imports the DB, builds the backend, boots the API and runs the integration
# tests. Requires: mysql client + server, g++, make, python3 + pytest/requests.
# Usage: bash scripts/run_integration_tests.sh
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_PASS="${DB_PASS:-root}"

echo "[1/5] Importing database schema + seed data ..."
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" < database/schema.sql
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" < database/seed.sql

echo "[2/5] Building backend ..."
make -C backend

echo "[3/5] Starting API server on :8080 ..."
./backend/bank_server &> /tmp/bms_server.log &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

echo "[4/5] Waiting for /api/health ..."
for _ in $(seq 1 30); do
  curl -sf http://localhost:8080/api/health > /dev/null && break
  sleep 1
done
curl -sf http://localhost:8080/api/health > /dev/null || { cat /tmp/bms_server.log; exit 1; }

echo "[5/5] Running integration tests ..."
python3 -m pytest -q tests/integration "$@"
echo "Done. (Skips = endpoints not implemented yet; they turn strict as owners finish.)"
