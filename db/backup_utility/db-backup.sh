#!/usr/bin/env bash
# Lablink Database backup script
# Creates database backup archive and uploads to remote storage
# shellcheck disable=SC2086

# Enable strict error handling
set -euo pipefail

# ============================================================================
# Configuration - Get paths and read environment variables
# ============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the project root directory
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Data directory where database data is stored (Docker named volume)
DATA_DIR="/var/lib/docker/volumes/deployment_postgres_data/_data"
# Local directory to store backup files
LOCAL_BACKUP_DIR="${LL_BACKUP_DIR:-${PROJECT_ROOT}/backups}"
# Whether to create a compressed archive of all data
ARCHIVE_ENABLED="${LL_ARCHIVE_ENABLED:-true}"
# Prefix for archive filenames
ARCHIVE_PREFIX="${LL_ARCHIVE_PREFIX:-lablink-db}"
# Paths to exclude from the archive (relative to DATA_DIR)
ARCHIVE_EXCLUDES="${LL_ARCHIVE_EXCLUDES:-}"
# Number of days to keep local backups
RETENTION_DAYS="${LL_RETENTION_DAYS:-7}"
# Command to run for remote sync (e.g., upload to GCS)
REMOTE_SYNC_CMD="${LL_REMOTE_SYNC_CMD:-}"
# Optional encryption command
ENCRYPT_CMD="${LL_ENCRYPT_CMD:-}"

# ============================================================================
# Helper Functions
# ============================================================================

# Log a message with timestamp
log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

# Log error and exit with non-zero status
fail() {
  log "ERROR: $*" >&2
  exit 1
}

# Check if a value is truthy (true, yes, 1, etc.)
is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|y|Y|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

# Try to create archive with current user first, then with non-interactive sudo if needed.
create_archive() {
  local tmp_archive="$1"
  shift
  local tar_cmd=("$@")
  local use_sudo_first=false

  # Avoid noisy tar permission errors by using sudo immediately
  # when the DB directory is not readable/traversable by current user.
  if [[ ! -r "${DATA_DIR}" || ! -x "${DATA_DIR}" ]]; then
    use_sudo_first=true
  fi

  if [[ "${use_sudo_first}" == "true" ]]; then
    log "Current user cannot read ${DATA_DIR}; using sudo -n for archive creation"
    if ! command -v sudo >/dev/null 2>&1; then
      fail "Archive requires elevated read access but sudo is unavailable"
    fi
    if ! sudo -n true >/dev/null 2>&1; then
      fail "Archive requires elevated read access and passwordless sudo is unavailable"
    fi
    if ! sudo -n "${tar_cmd[@]}"; then
      return 1
    fi
    sudo -n chown "$(id -u):$(id -g)" "${tmp_archive}" || true
    chmod u+rw "${tmp_archive}" || true
    return 0
  fi

  if "${tar_cmd[@]}"; then
    return 0
  fi

  log "Archive attempt failed as current user; retrying with sudo -n"
  if ! command -v sudo >/dev/null 2>&1; then
    fail "Archive failed and sudo is unavailable"
  fi
  if ! sudo -n true >/dev/null 2>&1; then
    fail "Archive failed and passwordless sudo is unavailable for this command"
  fi

  if ! sudo -n "${tar_cmd[@]}"; then
    return 1
  fi

  # Ensure the current user can read/upload the produced archive file.
  sudo -n chown "$(id -u):$(id -g)" "${tmp_archive}" || true
  chmod u+rw "${tmp_archive}" || true
  return 0
}

# ============================================================================
# Pre-flight Checks - Verify all requirements are met
# ============================================================================

# Check if database data directory exists
if [[ ! -d "${DATA_DIR}" ]]; then
  fail "Expected database data directory '${DATA_DIR}' does not exist"
fi

# Create local backup directory if it doesn't exist
mkdir -p "${LOCAL_BACKUP_DIR}"

# ============================================================================
# Step 1: Create Compressed Archive of Database Data
# ============================================================================

archive_path=""
last_backup=""

# Only create archive if ARCHIVE_ENABLED is set to true
if is_truthy "${ARCHIVE_ENABLED}"; then
  # Generate timestamp for unique archive filename
  timestamp="$(date '+%Y%m%d_%H%M%S')"
  archive_basename="${ARCHIVE_PREFIX}_${timestamp}.tar.gz"
  archive_path="${LOCAL_BACKUP_DIR}/${archive_basename}"
  tmp_archive="${archive_path}.in-progress"

  # Get parent directory and basename for tar command
  # e.g., if DATA_DIR is /var/lib/docker/volumes/deployment_postgres_data/_data
  # parent_dir will be /var/lib/docker/volumes/deployment_postgres_data
  # data_basename will be _data
  parent_dir="$(dirname "${DATA_DIR}")"
  data_basename="$(basename "${DATA_DIR}")"

  # Build tar command with compression
  tar_cmd=(tar --create --gzip --file "${tmp_archive}" --directory "${parent_dir}")

  # Add exclusions if configured
  if [[ -n "${ARCHIVE_EXCLUDES}" ]]; then
    IFS=':' read -r -a archive_excludes <<< "${ARCHIVE_EXCLUDES}"
    for rel_path in "${archive_excludes[@]}"; do
      rel_path_trimmed="${rel_path//[[:space:]]/}"
      if [[ -n "${rel_path_trimmed}" ]]; then
        tar_cmd+=(--exclude="${data_basename}/${rel_path_trimmed}")
      fi
    done
  fi

  # Add the directory to archive
  tar_cmd+=("${data_basename}")

  # Create the compressed archive
  log "Archiving ${DATA_DIR} -> ${archive_basename}"
  if create_archive "${tmp_archive}" "${tar_cmd[@]}"; then
    # Move the completed archive to its final location
    mv -f "${tmp_archive}" "${archive_path}"
    # Update last_backup to point to the archive (this will be uploaded to GCS)
    last_backup="${archive_path}"
    log "Archive created successfully: ${archive_path}"
  else
    rm -f "${tmp_archive}"
    fail "Failed to create archive ${archive_basename}"
  fi
else
  log "Archive creation disabled"
fi

# ============================================================================
# Step 2: Upload to Remote Storage (GCS)
# ============================================================================

# If a remote sync command is configured and we have a backup file to upload
if [[ -n "${REMOTE_SYNC_CMD}" && -n "${last_backup}" ]]; then
  log "Running remote sync command"

  # Write the remote sync command to a temporary script file
  # This allows for complex commands with variables
  cmd_script="$(mktemp)"
  printf '%s\n' "${REMOTE_SYNC_CMD}" > "${cmd_script}"

  # Execute the remote sync command with environment variables
  # LAST_BACKUP: Path to the backup file to upload
  # DATA_DIR: Path to the database data directory
  if ! env LAST_BACKUP="${last_backup}" DATA_DIR="${DATA_DIR}" bash "${cmd_script}"; then
    rm -f "${cmd_script}"
    fail "Remote sync command failed — skipping local cleanup to preserve backups"
  fi

  # Clean up the temporary script
  rm -f "${cmd_script}"
fi

# ============================================================================
# Step 3: Clean Up Old Local Backups
# Only runs after a successful upload (or if no remote sync is configured).
# This ensures local backups are never pruned when a backup/upload has failed.
# ============================================================================

# Delete local backup files older than RETENTION_DAYS
if [[ -n "${RETENTION_DAYS}" ]]; then
  log "Pruning local backups older than ${RETENTION_DAYS} day(s)"
  # Find and delete files in backup directory older than RETENTION_DAYS
  # -mtime +N means files modified more than N days ago
  find "${LOCAL_BACKUP_DIR}" -maxdepth 1 -type f -mtime +"${RETENTION_DAYS}" -print -delete || true
fi

# ============================================================================
# Backup Complete
# ============================================================================

log "Backup routine completed successfully"
