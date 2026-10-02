#!/usr/bin/env bash
# Cloud Hermes Core V1 — deploy (candidate environment). Secrets come from the environment
# or a secret manager; they are NEVER printed by this script.
#
# Unified deployment contract (see ROLLBACK-PLAN.md / DEPLOYMENT-REPORT.md):
#   DEPLOY_DIR          source/install dir          default: repo root (override for /opt/hermes-cloud)
#   HERMES_DATA_DIR     host DB directory           default: /var/lib/hermes-cloud
#   BACKUP_DIR          rollback backup directory   default: /var/backups/hermes-cloud
#   HEALTH_URL          loopback health endpoint    default: http://127.0.0.1:8080/api/hermes/v1/health
#   COMPOSE_PROJECT_NAME compose project name       default: hermes-cloud
#
# This script does NOT depend on HTTPS, a domain, or ports 80/443. It verifies the service
# is reachable on the loopback health URL only. Set DOCKER="sudo docker" if your user cannot
# reach the docker socket directly.
set -euo pipefail

# --- Unified, defaulted deployment variables (no contradictory hardcodes) ---
DEPLOY_DIR="${DEPLOY_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HERMES_DATA_DIR="${HERMES_DATA_DIR:-/var/lib/hermes-cloud}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/hermes-cloud}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8080/api/hermes/v1/health}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-hermes-cloud}"
DOCKER="${DOCKER:-docker}"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"

# docker compose wrapper that always pins the project name and compose file.
dc() { "$DOCKER" compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" "$@"; }

err() { echo "[deploy] ERROR: $*" >&2; }

# --- Validate required variables exist (names only; values are never printed) ---
require_nonempty() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    err "required variable $name is empty. Supply it via the environment / secret manager."
    return 1
  fi
}

require_nonempty HERMES_SECRET_KEY
require_nonempty ADMIN_INIT_TOKEN
# Provider is required for production, unless the mock provider is explicitly enabled (tests).
if [ "${HERMES_MOCK_PROVIDER:-0}" != "1" ]; then
  require_nonempty PROVIDER_BASE_URL
  require_nonempty PROVIDER_API_KEY
  require_nonempty PROVIDER_MODEL
fi

# --- Safely create + validate data and backup directories (no secret output) ---
mkdir -p "$HERMES_DATA_DIR" "$BACKUP_DIR"
if [ ! -w "$HERMES_DATA_DIR" ]; then err "data directory $HERMES_DATA_DIR is not writable."; exit 1; fi
if [ ! -w "$BACKUP_DIR" ]; then err "backup directory $BACKUP_DIR is not writable."; exit 1; fi

echo "[deploy] project:        $COMPOSE_PROJECT_NAME"
echo "[deploy] deploy dir:     $DEPLOY_DIR"
echo "[deploy] data dir:       $HERMES_DATA_DIR"
echo "[deploy] backup dir:     $BACKUP_DIR"
echo "[deploy] health url:     $HEALTH_URL"
echo "[deploy] mock provider:  ${HERMES_MOCK_PROVIDER:-0}"

# --- Render + validate the compose file before building ---
echo "[deploy] validating compose config..."
dc config >/dev/null

echo "[deploy] building image..."
dc build

echo "[deploy] starting (migrations run automatically on startup)..."
dc up -d

# --- Wait for BOTH container health and loopback HTTP health ---
echo "[deploy] waiting for healthy container + loopback health..."
HEALTHY=0
HTTP_OK=0
for i in $(seq 1 60); do
  STATUS="$("$DOCKER" inspect -f '{{.State.Health.Status}}' "$("$DOCKER" compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" ps -q hermes-cloud)" 2>/dev/null || true)"
  if [ "$STATUS" = "healthy" ]; then HEALTHY=1; fi
  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then HTTP_OK=1; fi
  if [ "$HEALTHY" = "1" ] && [ "$HTTP_OK" = "1" ]; then
    echo "[deploy] healthy."
    curl -fsS "$HEALTH_URL"
    exit 0
  fi
  sleep 2
done

# --- Timeout: report diagnostics WITHOUT leaking secrets ---
err "health check timed out"
echo "[deploy] --- docker compose ps ---"
dc ps
echo "[deploy] --- container health status ---"
"$DOCKER" inspect -f '{{.Name}} health={{.State.Health.Status}}' \
  "$("$DOCKER" compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" ps -q hermes-cloud)" 2>/dev/null || true
echo "[deploy] --- last logs (sanitised; no secrets/tokens/keys/passwords) ---"
dc logs --tail 50 hermes-cloud \
  | sed -E 's/(Authorization: Bearer|HERMES_SECRET_KEY=|PROVIDER_API_KEY=|ADMIN_INIT_TOKEN=)[^ ]+/<redacted>/g' \
  || true
exit 1
