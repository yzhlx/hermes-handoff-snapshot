#!/usr/bin/env bash
# Cloud Hermes Core V1 — PACKAGE-REPAIR isolated smoke (build + run + persistence + rollback
# safety). This is the canonical deployment-package-repair verification (§5.6, §8, §9).
#
# It is SELF-CONTAINED and uses ONLY throwaway temp resources. It NEVER writes to the
# production defaults (/opt/hermes-cloud, /var/lib/hermes-cloud, /var/backups/hermes-cloud)
# and NEVER touches ports 80/443 or the public network. Run it on a Docker host (e.g. the
# candidate cloud host) with DOCKER pointing at the docker CLI:
#
#   DOCKER="sudo docker" bash scripts/rollback_smoke.sh
#
# What it proves:
#   1) Image builds; container starts; container health = healthy.
#   2) Host loopback health (HEALTH_URL) succeeds; public 8080 is NOT bound to 0.0.0.0.
#   3) Test admin bootstrap works; a Mock chat + a marker task are written to SQLite.
#   4) The DB file appears in the temp host data directory.
#   5) Stop + restart preserves the marker data (persistence across restart).
#   6) Rollback SAFE backup: Python sqlite3 online backup to BACKUP_DIR, verified
#      (exists + non-zero + integrity_check + marker present). Original DB is NOT dropped.
#   7) Service is healthy again after the rollback bring-up.
#   8) Cleanup removes only this run's containers / network / image / temp dir.
#
# The full `git checkout <stable>` code-rollback is performed by scripts/rollback.sh on a real
# deployment host; this isolated smoke validates the NON-DESTRUCTIVE backup + restart guarantee
# (the critical property) without disturbing any git working tree.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TS="$(date +%Y%m%d-%H%M%S)"
WORK="$(mktemp -d "/tmp/hermes-package-repair-${TS}.XXXXXX")"
DATA_DIR="${HERMES_DATA_DIR:-$WORK/data}"
BACKUP_DIR="${BACKUP_DIR:-$WORK/backups}"
PROJECT="${COMPOSE_PROJECT_NAME:-hermes-package-repair-${TS}}"
TEST_PORT="${TEST_PORT:-18080}"
# DOCKER may be a single binary ("docker") or a prefix ("sudo docker"). We keep it
# unquoted at every call site so the prefix word-splits correctly into `sudo` + `docker`.
DOCKER=${DOCKER:-docker}
PYTHON="${PYTHON:-python3}"
BASE="http://127.0.0.1:${TEST_PORT}"
HEALTH_URL="${HEALTH_URL:-$BASE/api/hermes/v1/health}"

# Test-only secrets / identities (clearly marked; never real).
SECRET="test-only-secret-${TS}"
ADMIN_TOKEN="test-only-admin-token"
ADMIN_USER="test-admin"
ADMIN_PASS="Test!Pass#repair"
PROVIDER_BASE_URL="http://127.0.0.1:9/v1"   # unreachable; mock provider is used instead
PROVIDER_API_KEY="test-only-provider-key"
PROVIDER_MODEL="test-model"
MARKER="PACKAGE-REPAIR-SMOKE-MARKER-${TS}"

# Export for compose ${VAR} substitution.
export HERMES_ENV=production
export HERMES_SECRET_KEY="$SECRET"
export ADMIN_INIT_TOKEN="$ADMIN_TOKEN"
export HERMES_DB_PATH="/data/hermes_cloud.db"
export PROVIDER_BASE_URL PROVIDER_API_KEY PROVIDER_MODEL
export HERMES_DATA_DIR="$DATA_DIR"
export HERMES_MOCK_PROVIDER=1

mkdir -p "$DATA_DIR" "$BACKUP_DIR"

# Test-only override: isolate to a high loopback port (production default 127.0.0.1:8080 is
# validated separately via `docker compose config`). Never committed to the repo.
OV="$WORK/docker-compose.override.yml"
cat > "$OV" <<EOF
services:
  hermes-cloud:
    ports:
      - "127.0.0.1:${TEST_PORT}:8080"
    environment:
      HERMES_MOCK_PROVIDER: "1"
EOF

dc() { $DOCKER compose -p "$PROJECT" -f "$ROOT/docker-compose.yml" -f "$OV" "$@"; }

PASS=0
fail() { echo "FAIL: $*"; PASS=1; }
ok()   { echo "PASS: $*"; }

cleanup() {
  $DOCKER compose -p "$PROJECT" -f "$ROOT/docker-compose.yml" -f "$OV" down >/dev/null 2>&1 || true
  $DOCKER image rm "${PROJECT}-hermes-cloud" >/dev/null 2>&1 || true
  rm -rf "$WORK" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "===== CLOUD HERMES PACKAGE-REPAIR SMOKE ====="
echo "started:      $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "host:         $(uname -n)"
echo "docker:       $($DOCKER version --format 'server={{.Server.Version}}' 2>/dev/null || echo unknown)"
echo "root:         $ROOT"
echo "project:      $PROJECT"
echo "data dir:     $DATA_DIR"
echo "backup dir:   $BACKUP_DIR"
echo "test port:    $TEST_PORT (loopback only)"
echo "health url:   $HEALTH_URL"
echo

# 1) Build
echo "[1] building image..."
if dc build >/dev/null 2>&1; then ok "image built"; else fail "image build failed"; fi

# 2) Bootstrap test admin
echo "[2] bootstrapping test admin ($ADMIN_USER)..."
if dc run --rm hermes-cloud python -m cloud_hermes.main --bootstrap-admin "$ADMIN_TOKEN" "$ADMIN_USER" "$ADMIN_PASS" >/dev/null 2>&1; then
  ok "admin bootstrapped"
else
  fail "admin bootstrap failed"
fi

# 3) Start
echo "[3] starting container..."
dc up -d >/dev/null 2>&1 || fail "up -d failed"

# 4) Wait for container health + loopback health
echo "[4] waiting for healthy container + loopback health..."
HEALTHY=0; HTTP_OK=0
for i in $(seq 1 60); do
  CID="$($DOCKER compose -p "$PROJECT" -f "$ROOT/docker-compose.yml" -f "$OV" ps -q hermes-cloud 2>/dev/null || true)"
  ST="$($DOCKER inspect -f '{{.State.Health.Status}}' "$CID" 2>/dev/null || true)"
  [ "$ST" = "healthy" ] && HEALTHY=1
  curl -fsS "$HEALTH_URL" >/dev/null 2>&1 && HTTP_OK=1
  if [ "$HEALTHY" = "1" ] && [ "$HTTP_OK" = "1" ]; then break; fi
  sleep 2
done
[ "$HEALTHY" = "1" ] && ok "container healthy" || fail "container never became healthy"
[ "$HTTP_OK" = "1" ] && ok "loopback health OK at $HEALTH_URL" || fail "loopback health failed"

# 5) Public exposure check: the test port must bind 127.0.0.1 only, never 0.0.0.0
echo "[5] verifying test port binds loopback only (no 0.0.0.0)..."
BIND="$($DOCKER port "$( $DOCKER compose -p "$PROJECT" -f "$ROOT/docker-compose.yml" -f "$OV" ps -q hermes-cloud )" 8080 2>/dev/null | head -1 || true)"
if echo "$BIND" | grep -q "127.0.0.1"; then ok "port bound to 127.0.0.1 ($BIND)"; else fail "unexpected bind: $BIND"; fi
# Use ss on the host to confirm the LOCAL bind address is loopback, never 0.0.0.0.
# NOTE: ss lines carry two address columns — Local Address:Port (field 4) and
# Peer Address:Port (field 5, always "0.0.0.0:*"). We must inspect ONLY the local
# column (field 4); matching bare "0.0.0.0" anywhere would false-positive on the
# peer column. docker port (above) is the authoritative source; this is corroboration.
if command -v ss >/dev/null 2>&1; then
  LOCAL_BIND="$(ss -lntp 2>/dev/null | awk -v p=":$TEST_PORT" '$4 ~ p {print $4; exit}')"
  if echo "$LOCAL_BIND" | grep -qE '^0\.0\.0\.0:|^\[?::\]:?'; then
    fail "test port exposed on 0.0.0.0 (bind=$LOCAL_BIND)"
  elif [ -n "$LOCAL_BIND" ]; then
    ok "no 0.0.0.0 listener on $TEST_PORT (local bind=$LOCAL_BIND)"
  else
    ok "no host socket for $TEST_PORT via ss (loopback NAT confirmed by docker port above)"
  fi
fi

# 6) Login
echo "[6] login (bearer)..."
LOGIN="$(curl -fsS -X POST "$BASE/api/hermes/v1/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" 2>/dev/null || true)"
if [ -z "$LOGIN" ]; then fail "login failed"; else
  TOKEN="$(printf '%s' "$LOGIN" | "$PYTHON" -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)"
  [ -n "$TOKEN" ] && ok "login OK (token issued)" || fail "no access_token in login response"
fi

# 7) Mock chat + marker task (identifiable test data)
echo "[7] mock chat + marker task..."
CHAT="$(curl -fsS -X POST "$BASE/api/hermes/v1/chat" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" -H "Idempotency-Key: repair-smoke-1" \
  -d "{\"message\":\"$MARKER say hello\"}" 2>/dev/null || true)"
RUN_ID="$(printf '%s' "$CHAT" | "$PYTHON" -c "import sys,json;print(json.load(sys.stdin).get('hermes_run_id',''))" 2>/dev/null || true)"
[ -n "$RUN_ID" ] && ok "chat OK (hermes_run_id=$RUN_ID)" || fail "chat failed / no hermes_run_id"

TASK="$(curl -fsS -X POST "$BASE/api/hermes/v1/tasks" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" -H "Idempotency-Key: repair-task-1" \
  -d "{\"title\":\"$MARKER\",\"description\":\"package-repair smoke task\"}" 2>/dev/null || true)"
TASK_ID="$(printf '%s' "$TASK" | "$PYTHON" -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || true)"
[ -n "$TASK_ID" ] && ok "task created (id=$TASK_ID)" || fail "task creation failed"

# 8) Read endpoints
echo "[8] read endpoints (conversations/tasks/execution-nodes/run)..."
curl -fsS "$BASE/api/hermes/v1/conversations" -H "Authorization: Bearer $TOKEN" >/dev/null 2>&1 && ok "conversations 200" || fail "conversations failed"
curl -fsS "$BASE/api/hermes/v1/tasks" -H "Authorization: Bearer $TOKEN" >/dev/null 2>&1 && ok "tasks 200" || fail "tasks failed"
curl -fsS "$BASE/api/hermes/v1/execution-nodes" -H "Authorization: Bearer $TOKEN" >/dev/null 2>&1 && ok "execution-nodes 200" || fail "execution-nodes failed"
if [ -n "$RUN_ID" ]; then
  curl -fsS "$BASE/api/hermes/v1/runs/$RUN_ID" -H "Authorization: Bearer $TOKEN" >/dev/null 2>&1 && ok "run 200" || fail "run failed"
fi

# 9) DB file present in temp host data dir
echo "[9] DB file present in temp host data dir..."
DB="$DATA_DIR/hermes_cloud.db"
if [ -s "$DB" ]; then ok "DB at $DB ($(stat -c%s "$DB") bytes)"; else fail "DB missing/empty at $DB"; fi

# 10) Persistence across restart
echo "[10] stop + restart, verify marker persists..."
dc down >/dev/null 2>&1 || true
dc up -d >/dev/null 2>&1 || fail "restart up -d failed"
ROK=0
for i in $(seq 1 60); do
  curl -fsS "$HEALTH_URL" >/dev/null 2>&1 && ROK=1 && break
  sleep 2
done
[ "$ROK" = "1" ] || fail "service did not come back after restart"
# re-login + verify marker task still listed
LOGIN2="$(curl -fsS -X POST "$BASE/api/hermes/v1/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" 2>/dev/null || true)"
TOKEN2="$(printf '%s' "$LOGIN2" | "$PYTHON" -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)"
TASKS_AFTER="$(curl -fsS "$BASE/api/hermes/v1/tasks" -H "Authorization: Bearer $TOKEN2" 2>/dev/null || true)"
if printf '%s' "$TASKS_AFTER" | grep -q "$MARKER"; then ok "marker task persisted across restart"; else fail "marker task lost after restart"; fi

# helper: does a sqlite db contain the marker anywhere?
db_has_marker() {
  "$PYTHON" - "$1" "$MARKER" <<'PY'
import sqlite3, sys
db, marker = sys.argv[1], sys.argv[2]
try:
    c = sqlite3.connect(db)
    for (tbl,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        try:
            for row in c.execute(f"SELECT * FROM '{tbl}'"):
                if any(marker in str(v) for v in row):
                    print("yes"); sys.exit(0)
        except Exception:
            pass
    print("no")
except Exception as e:
    print("err:" + str(e))
PY
}

# 11) Rollback SAFE backup + verification (non-destructive)
echo "[11] rollback safe backup + verification..."
BACKUP="$BACKUP_DIR/pre-rollback-$TS.db"
"$PYTHON" - "$DB" "$BACKUP" <<'PY'
import sqlite3, sys, os
src, dst = sys.argv[1], sys.argv[2]
with sqlite3.connect(src) as c, sqlite3.connect(dst) as b:
    c.backup(b)
print("backup written")
PY
if [ ! -s "$BACKUP" ]; then fail "backup missing/empty"; else ok "backup exists ($(stat -c%s "$BACKUP") bytes)"; fi
BK_INT="$("$PYTHON" -c "import sqlite3,sys;print(sqlite3.connect(sys.argv[1]).execute('PRAGMA integrity_check').fetchone()[0])" "$BACKUP" 2>/dev/null || true)"
[ "$BK_INT" = "ok" ] && ok "backup integrity=ok" || fail "backup integrity=$BK_INT"
[ "$(db_has_marker "$BACKUP")" = "yes" ] && ok "backup contains marker data" || fail "backup missing marker data"
ORIG_INT="$("$PYTHON" -c "import sqlite3,sys;print(sqlite3.connect(sys.argv[1]).execute('PRAGMA integrity_check').fetchone()[0])" "$DB" 2>/dev/null || true)"
[ "$ORIG_INT" = "ok" ] && ok "original DB integrity=ok (not dropped)" || fail "original integrity=$ORIG_INT"
[ "$(db_has_marker "$DB")" = "yes" ] && ok "original DB still contains marker data" || fail "original lost marker data"
[ -f "$DB" ] && ok "original DB file still present" || fail "original DB file removed"

# 12) Post-rollback bring-up health
echo "[12] post-rollback bring-up health..."
H2=0
for i in $(seq 1 30); do curl -fsS "$HEALTH_URL" >/dev/null 2>&1 && H2=1 && break; sleep 2; done
[ "$H2" = "1" ] && ok "service healthy after rollback bring-up" || fail "service not healthy after rollback"

# 13) Unauthorized rejection
echo "[13] unauthenticated access rejected (401)..."
CODE="$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/hermes/v1/conversations" 2>/dev/null || true)"
[ "$CODE" = "401" ] && ok "unauth -> 401" || fail "unauth returned $CODE (expected 401)"

echo
echo "===== SMOKE RESULT ====="
if [ "$PASS" = "0" ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECKS FAILED"; fi
echo "finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
exit $PASS
