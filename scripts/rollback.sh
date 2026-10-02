#!/usr/bin/env bash
# Cloud Hermes Core V1 — rollback to a previously verified stable build.
#
# SAFETY (never negotiable):
#   * The cloud DB is NEVER dropped and the data directory is NEVER wiped.
#   * The pre-rollback DB is copied with a SAFE SQLite online backup (sqlite3 backup API)
#     to BACKUP_DIR/pre-rollback-<ts>.db, then verified (exists + non-zero + integrity_check).
#   * The real <stable_commit> is only checked out AFTER the backup is verified.
#   * On any failure the DB and backup are left untouched.
#
# Unified deployment contract (see deploy.sh):
#   DEPLOY_DIR, HERMES_DATA_DIR, BACKUP_DIR, HEALTH_URL, COMPOSE_PROJECT_NAME
#
# DB path contract: the cloud DB lives at ${HERMES_DATA_DIR}/hermes_cloud.db on the HOST
# (bind-mounted to /data in the container). We read from there — never from
# ${DEPLOY_DIR}/data/hermes_cloud.db.
#
# Set DOCKER="sudo docker" if your user cannot reach the docker socket directly.
set -euo pipefail

STABLE_COMMIT="${1:?Usage: rollback.sh <stable_commit>}"

# --- Unified, defaulted variables (no contradictory hardcodes) ---
DEPLOY_DIR="${DEPLOY_DIR:-/opt/hermes-cloud}"
HERMES_DATA_DIR="${HERMES_DATA_DIR:-/var/lib/hermes-cloud}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/hermes-cloud}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8080/api/hermes/v1/health}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-hermes-cloud}"
DOCKER="${DOCKER:-docker}"
PYTHON="${PYTHON:-python3}"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
DB="${HERMES_DATA_DIR}/hermes_cloud.db"
TS="$(date +%Y%m%d-%H%M%S)"

dc() { "$DOCKER" compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" "$@"; }
err() { echo "[rollback] ERROR: $*" >&2; }

echo "[rollback] target stable commit: ${STABLE_COMMIT}"
echo "[rollback] deploy dir:           ${DEPLOY_DIR}"
echo "[rollback] data dir:             ${HERMES_DATA_DIR}"
echo "[rollback] backup dir:           ${BACKUP_DIR}"
echo "[rollback] health url:           ${HEALTH_URL}"

# --- 0) Validate the stable commit argument looks like a ref (cheap guard) ---
if [ -d "${DEPLOY_DIR}/.git" ]; then
  if ! git -C "$DEPLOY_DIR" rev-parse --verify "$STABLE_COMMIT" >/dev/null 2>&1; then
    err "stable commit '$STABLE_COMMIT' is not a valid git ref in $DEPLOY_DIR."
    exit 1
  fi
fi

# --- 1) Stop the candidate service (keep DB on host; no writer after this) ---
echo "[rollback] stopping candidate service..."
# Optional systemd unit: only stop if it actually exists (never treat as a hard dependency).
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q '^hermes-cloud\.service'; then
  echo "[rollback] stopping systemd unit hermes-cloud.service (present)..."
  systemctl stop hermes-cloud.service || true
fi
dc down || true

# --- 2) Ensure backup dir exists, then SAFELY back up the cloud DB (never drops it) ---
mkdir -p "$BACKUP_DIR"
BACKUP="${BACKUP_DIR}/pre-rollback-${TS}.db"

if [ -f "$DB" ]; then
  echo "[rollback] performing safe SQLite backup of $DB -> $BACKUP ..."
  "$PYTHON" - "$DB" "$BACKUP" <<'PY'
import sqlite3, sys, os
src, dst = sys.argv[1], sys.argv[2]
if not os.path.exists(src):
    sys.exit("source DB missing")
with sqlite3.connect(src) as c, sqlite3.connect(dst) as b:
    c.backup(b)   # consistent online backup; captures committed WAL state
print("backup written")
PY
  # --- 3) Verify backup: exists + non-zero + integrity_check ---
  if [ ! -s "$BACKUP" ]; then err "backup is missing or zero-sized."; exit 1; fi
  BK_INT="$("$PYTHON" -c "import sqlite3,sys;print(sqlite3.connect(sys.argv[1]).execute('PRAGMA integrity_check').fetchone()[0])" "$BACKUP")"
  if [ "$BK_INT" != "ok" ]; then err "backup integrity_check failed: $BK_INT"; exit 1; fi
  echo "[rollback] backup verified (exists, non-zero, integrity=ok): $BACKUP"

  # Also verify the ORIGINAL is intact (it must not have been touched).
  ORIG_INT="$("$PYTHON" -c "import sqlite3,sys;print(sqlite3.connect(sys.argv[1]).execute('PRAGMA integrity_check').fetchone()[0])" "$DB")"
  if [ "$ORIG_INT" != "ok" ]; then err "original DB integrity_check failed: $ORIG_INT"; exit 1; fi
  echo "[rollback] original DB intact (integrity=ok); DB is NOT dropped."
else
  echo "[rollback] no cloud DB at $DB yet — nothing to back up (fresh deploy)."
fi

# --- 4) Only now restore the previous stable commit (code/data separation: DB stays on host) ---
echo "[rollback] checking out stable commit ${STABLE_COMMIT}..."
git -C "$DEPLOY_DIR" fetch --all || true
git -C "$DEPLOY_DIR" checkout "$STABLE_COMMIT"

# --- 5) Rebuild + restart from the stable commit ---
echo "[rollback] rebuilding + restarting from stable commit..."
dc up -d --build

# --- 6) Verify loopback health (HTTP, never https://127.0.0.1) ---
echo "[rollback] verifying health at ${HEALTH_URL} ..."
for i in $(seq 1 30); do
  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    echo "[rollback] OK: stable build healthy at ${STABLE_COMMIT}"
    curl -fsS "$HEALTH_URL"
    echo "[rollback] done. Cloud data preserved at ${HERMES_DATA_DIR}; backup at ${BACKUP}."
    exit 0
  fi
  sleep 2
done

err "stable build failed health check — DB and backup were left untouched."
exit 1
