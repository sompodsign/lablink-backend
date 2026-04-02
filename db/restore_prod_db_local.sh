#!/usr/bin/env bash
# Restore production PostgreSQL backup from GCS into the LOCAL dev environment.
# Designed for Mac + Docker Desktop where volumes are not directly accessible.
#
# Usage:
#   restore_prod_db_local.sh [backup-name-or-gs-uri] [--yes]
#
# Examples:
#   restore_prod_db_local.sh                      # restore latest backup
#   restore_prod_db_local.sh lablink-db_20260323_091111.tar.gz
#   restore_prod_db_local.sh gs://home-server-ss/lablink-backup/lablink-db_20260323_091111.tar.gz --yes
#
# Notes:
#   - Omitting the backup argument means "restore the latest backup from GCS".
#   - --yes (or FORCE_RESTORE=true) skips the confirmation prompt.
#   - GCS operations run inside a Docker container using google/cloud-sdk:slim.
#   - On Mac, Docker volumes are managed by the VM; this script uses a helper
#     container to write into the volume without requiring sudo.

# Re-exec with bash if launched via `sh script.sh`.
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── LabLink local defaults ────────────────────────────────────────────────────
# Local Docker volume name (matches docker-compose.yml: postgres_data)
DB_VOLUME="${LL_DB_VOLUME:-lablink-backend_postgres_data}"
ARCHIVE_PREFIX="${LL_ARCHIVE_PREFIX:-lablink-db}"
BUCKET_NAME="${GCS_BUCKET_NAME:-home-server-ss}"
BUCKET_PATH="${GCS_BUCKET_PATH:-lablink-backup}"
SERVICE_ACCOUNT_KEY="${GCS_SERVICE_ACCOUNT_KEY:-}"
GCLOUD_IMAGE="${GCLOUD_IMAGE:-google/cloud-sdk:slim}"
# Default to non-interactive for local convenience (no sudo/TTY needed).
FORCE_RESTORE="${FORCE_RESTORE:-true}"
DB_CONTAINER="${LL_DB_CONTAINER:-lablink_postgres}"
# ──────────────────────────────────────────────────────────────────────────────

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

step() {
  local n="$1"; local total="$2"; local msg="$3"
  printf '\n[%s] ── Step %s/%s: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "${n}" "${total}" "${msg}"
}

fail() {
  log "ERROR: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

resolve_service_account_key() {
  if [[ -n "${SERVICE_ACCOUNT_KEY}" ]]; then
    printf '%s\n' "${SERVICE_ACCOUNT_KEY}"
    return 0
  fi

  local -a candidates=(
    "${PROJECT_ROOT}/env/service-accounts/gcs_sa.json"
  )
  local key_path
  for key_path in "${candidates[@]}"; do
    if [[ -f "${key_path}" ]]; then
      printf '%s\n' "${key_path}"
      return 0
    fi
  done

  # Return first preferred path for a clearer error message when none exist.
  printf '%s\n' "${candidates[0]}"
}

run_gcloud_storage() {
  local -a docker_args
  docker_args=(
    run --rm
    --user "$(id -u):$(id -g)"
    -e HOME=/tmp
    -e CLOUDSDK_CONFIG=/tmp/.gcloud
    -v "${SERVICE_ACCOUNT_KEY}:/workspace/sa_key.json:ro"
  )

  if [[ "${1:-}" == "--mount-output" ]]; then
    local output_dir="$2"
    [[ -n "${output_dir}" ]] || fail "Missing output directory for --mount-output"
    docker_args+=(-v "${output_dir}:/workspace/out")
    shift 2
  fi

  docker "${docker_args[@]}" "${GCLOUD_IMAGE}" bash -lc '
    set -euo pipefail
    gcloud auth activate-service-account --key-file=/workspace/sa_key.json --quiet
    gcloud storage "$@"
  ' _ "$@"
}

# ── Argument parsing ───────────────────────────────────────────────────────────
backup_ref=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      sed -n '/^# Usage/,/^[^#]/{ /^[^#]/d; s/^# \{0,2\}//; p }' "$0"
      exit 0
      ;;
    -y|--yes)
      FORCE_RESTORE="true"
      shift
      ;;
    *)
      if [[ -z "${backup_ref}" ]]; then
        backup_ref="$1"
        shift
      else
        fail "Unexpected argument: $1"
      fi
      ;;
  esac
done

# ── Pre-flight checks ──────────────────────────────────────────────────────────
step 1 6 'Pre-flight checks'
require_cmd docker
require_cmd tar

log 'Resolving GCS service account key'
SERVICE_ACCOUNT_KEY="$(resolve_service_account_key)"
[[ -f "${SERVICE_ACCOUNT_KEY}" ]] || fail "Service account key not found: ${SERVICE_ACCOUNT_KEY}"
log "Using service account key: ${SERVICE_ACCOUNT_KEY}"

log "Verifying Docker volume: ${DB_VOLUME}"
# Verify the local Docker volume exists
docker volume inspect "${DB_VOLUME}" > /dev/null 2>&1 || \
  fail "Local Docker volume not found: ${DB_VOLUME}. Is the dev stack running? (docker compose up -d db)"
log "Volume found: ${DB_VOLUME}"

# ── Resolve backup URI ─────────────────────────────────────────────────────
step 2 6 'Resolving backup URI'
if [[ -n "${backup_ref}" ]]; then
  if [[ "${backup_ref}" == gs://* ]]; then
    backup_uri="${backup_ref}"
  else
    backup_uri="gs://${BUCKET_NAME}/${BUCKET_PATH}/${backup_ref}"
  fi
  log "Using specified backup: ${backup_uri}"
else
  log "No backup specified; listing latest from gs://${BUCKET_NAME}/${BUCKET_PATH}/"
  backup_uri="$(run_gcloud_storage ls "gs://${BUCKET_NAME}/${BUCKET_PATH}/${ARCHIVE_PREFIX}_*.tar.gz" 2>/dev/null | sort | tail -n 1 || true)"
  [[ -n "${backup_uri}" ]] || fail "No matching backups found in gs://${BUCKET_NAME}/${BUCKET_PATH}/"
  log "Latest backup: ${backup_uri}"
fi

# ── Confirmation prompt ────────────────────────────────────────────────────────
if [[ "${FORCE_RESTORE}" != "true" && "${FORCE_RESTORE}" != "1" ]]; then
  if [[ ! -t 0 ]]; then
    fail "Non-interactive shell detected. Re-run with --yes or FORCE_RESTORE=true."
  fi
  echo "WARNING: This will DELETE and replace data in Docker volume: ${DB_VOLUME}"
  echo "Backup source: ${backup_uri}"
  read -r -p "Type RESTORE to continue: " confirm
  [[ "${confirm}" == "RESTORE" ]] || fail "Confirmation failed. Aborting."
fi

# ── Download & extract ───────────────────────────────────────────────────
step 3 6 'Downloading backup from GCS'
tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

archive_file="${tmp_dir}/restore.tar.gz"
extract_root="${tmp_dir}/extract"
mkdir -p "${extract_root}"

log "Downloading: ${backup_uri}"
run_gcloud_storage --mount-output "${tmp_dir}" cp "${backup_uri}" /workspace/out/restore.tar.gz
log "Download complete: ${archive_file}"

step 4 6 'Extracting backup archive'
tar -xzf "${archive_file}" -C "${extract_root}"
log "Extracted to: ${extract_root}"

# Locate the PostgreSQL data directory inside the archive
# Try the well-known inner directory name first, then fall back to heuristics.
step 5 6 'Locating PostgreSQL data directory in archive'
source_data_dir=""
expected_dir="${extract_root}/_data"
if [[ -d "${expected_dir}" ]]; then
  source_data_dir="${expected_dir}"
else
  source_data_dir="$(find "${extract_root}" -type f -name PG_VERSION -printf '%h\n' | head -n 1 || true)"
  [[ -n "${source_data_dir}" ]] || source_data_dir="$(find "${extract_root}" -type d -name "_data" | head -n 1 || true)"
  [[ -n "${source_data_dir}" ]] || fail "Could not find a PostgreSQL data directory in the extracted archive."
fi
log "Using source data dir: ${source_data_dir}"

# ── Stop container, swap data via helper container, restart ───────────────────
# Mac Docker Desktop volumes live inside a Linux VM; we cannot access them from
# the macOS host. Instead, we mount the volume into a temporary Alpine container
# and perform the wipe + copy there (no sudo required).
step 6 6 'Restoring data into Docker volume'
db_was_running="false"
if docker inspect "${DB_CONTAINER}" > /dev/null 2>&1; then
  if [[ "$(docker inspect -f '{{.State.Running}}' "${DB_CONTAINER}")" == "true" ]]; then
    log "Stopping DB container: ${DB_CONTAINER}"
    docker stop "${DB_CONTAINER}" > /dev/null
    db_was_running="true"
    log "Container stopped"
  fi
else
  log "DB container '${DB_CONTAINER}' not found; will restore into volume directly."
fi

log "Wiping volume and copying backup (this may take a moment...)"
docker run --rm \
  -v "${source_data_dir}:/restore_src:ro" \
  -v "${DB_VOLUME}:/pgdata" \
  alpine sh -c '
    find /pgdata -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    cp -a /restore_src/. /pgdata/
    chown -R 999:999 /pgdata
  '
log "Volume restore complete"

if [[ "${db_was_running}" == "true" ]]; then
  log "Starting DB container: ${DB_CONTAINER}"
  docker start "${DB_CONTAINER}" > /dev/null
fi

log "Restore completed successfully from ${backup_uri}"
