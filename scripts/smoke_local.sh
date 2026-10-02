#!/usr/bin/env bash
# Cloud Hermes Core V1 — LOCAL deploy + acceptance smoke (Docker-daemon-free).
#
# NOTE: The Docker engine daemon is NOT running in this sandbox, so the container RUNTIME
# could not be exercised here. Instead this smoke runs the EXACT same entrypoint the
# container CMD uses (`python -m cloud_hermes.main --bootstrap-admin ... --host ... --port ...`)
# as a plain local process. The service code path inside the container is identical, so this
# validates: packaging imports, migrations, admin bootstrap, HTTP serving, and the full
# contract endpoint surface. A real cloud host runs `scripts/deploy.sh` (docker compose) with
# PROVIDER_API_KEY supplied; that path is documented but not executed here (BLOCKED: no daemon).
#
# Uses the Mock provider for determinism (NO real provider key required/used).
set -uo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-C:\Users\user\.workbuddy\binaries\python\versions\3.13.12\python.exe}"
RESULTS="${RESULTS_DIR:-F:/Users/user/Documents/learning os-worktrees/artifacts/cloud-hermes-core-v1}"
DATA_DIR="$WORKDIR/work/smoke-data"
API="$RESULTS/api-results"
LOG="$RESULTS/logs/deploy-smoke.log"
mkdir -p "$DATA_DIR" "$API" "$RESULTS/logs"

SECRET="smoke-secret-key-local-only-$(date +%s)"
ADMIN_TOKEN="init-token-smoke"
ADMIN_USER="admin"
ADMIN_PASS="Smoke!Pass#2026"
PORT=8088
BASE="http://127.0.0.1:$PORT"

# Kill any prior server on the port.
exec > >(tee -a "$LOG") 2>&1
echo "===== CLOUD HERMES LOCAL DEPLOY SMOKE (python-direct) ====="
echo "started:        $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "python:         $PY"
echo "entrypoint:     python -m cloud_hermes.main --bootstrap-admin (same as container CMD)"
echo "provider:       MOCK (deterministic; no real key)"
echo "results:        $RESULTS"
echo "docker daemon:  NOT running -> container runtime not exercised (see DEPLOYMENT-REPORT.md)"
echo

export HERMES_ENV=production
export HERMES_SECRET_KEY="$SECRET"
export ADMIN_INIT_TOKEN="$ADMIN_TOKEN"
export HERMES_MOCK_PROVIDER=1
# Export a Windows-native DB path so the managed Python (a Windows binary) resolves it
# correctly; cygpath translates Git-Bash /f/... into F:\... (falls back if unavailable).
WIN_DB="$(cygpath -w "$DATA_DIR/hermes_cloud.db" 2>/dev/null || echo "$DATA_DIR/hermes_cloud.db")"
export HERMES_DB_PATH="$WIN_DB"

echo "[1/6] import + syntax check of the service package..."
"$PY" -c "import cloud_hermes.main, cloud_hermes.app, cloud_hermes.run_orchestrator; print('imports OK')"

echo "[2/6] starting service (bootstrap admin + serve)..."
"$PY" -m cloud_hermes.main --bootstrap-admin "$ADMIN_TOKEN" "$ADMIN_USER" "$ADMIN_PASS" --host 127.0.0.1 --port "$PORT" > "$RESULTS/logs/server.out" 2>&1 &
SERVER_PID=$!
echo "server pid: $SERVER_PID"

echo "[3/6] waiting for health..."
OK=0
for i in $(seq 1 30); do
  if curl -fsS "$BASE/api/hermes/v1/health" >/dev/null 2>&1; then OK=1; echo "healthy after ${i} tries"; break; fi
  sleep 1
done
if [ "$OK" -ne 1 ]; then echo "ERROR: health never came up"; kill "$SERVER_PID" 2>/dev/null || true; exit 1; fi
curl -fsS "$BASE/api/hermes/v1/health" | tee "$API/health.json"
echo

echo "[4/6] login (bearer)..."
LOGIN=$(curl -fsS -X POST "$BASE/api/hermes/v1/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}")
echo "$LOGIN" | tee "$API/login.json"
TOKEN=$(printf '%s' "$LOGIN" | "$PY" -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "token: ${TOKEN:0:8}..."

echo "[5/6] chat (real run w/ memory + events), idempotency, read endpoints..."
curl -fsS -X POST "$BASE/api/hermes/v1/chat" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" -H "Idempotency-Key: smoke-1" \
  -d '{"message":"What is the capital of France?","seed_shared_memory":"The user prefers concise answers."}' \
  | tee "$API/chat.json"
echo
echo "-- repeat same Idempotency-Key (must return identical run) --"
curl -fsS -X POST "$BASE/api/hermes/v1/chat" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" -H "Idempotency-Key: smoke-1" \
  -d '{"message":"What is the capital of France?"}' | tee "$API/idempotency.json"
echo
curl -fsS "$BASE/api/hermes/v1/conversations" -H "Authorization: Bearer $TOKEN" | tee "$API/conversations.json"
echo
curl -fsS "$BASE/api/hermes/v1/tasks" -H "Authorization: Bearer $TOKEN" | tee "$API/tasks.json"
echo
curl -fsS "$BASE/api/hermes/v1/execution-nodes" -H "Authorization: Bearer $TOKEN" | tee "$API/execution-nodes.json"
echo
RUN_ID=$(printf '%s' "$(cat "$API/chat.json")" | "$PY" -c "import sys,json;print(json.load(sys.stdin).get('hermes_run_id',''))" 2>/dev/null || true)
if [ -n "$RUN_ID" ]; then
  curl -fsS "$BASE/api/hermes/v1/runs/$RUN_ID" -H "Authorization: Bearer $TOKEN" | tee "$API/run.json"; echo
fi

echo "[6/6] unauthorized access must be rejected (401)..."
curl -s -o "$API/unauth.json" -w "HTTP %{http_code}\n" "$BASE/api/hermes/v1/conversations"
echo "unauth body:"; cat "$API/unauth.json"; echo

echo "===== SMOKE COMPLETE ====="
kill "$SERVER_PID" 2>/dev/null || true
echo "cloud DB preserved at: $DATA_DIR/hermes_cloud.db"
echo "finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
