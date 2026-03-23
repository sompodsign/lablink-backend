#!/usr/bin/env bash
# Sync the production PostgreSQL data directory from the remote server
# to the local db-host directory for local development.
#
# Remote: shampad@shampad.ddns.net  →  Docker volume _data dir
# Local:  ./db-host  (mounted as the postgres data dir in local docker-compose)

set -euo pipefail

SOURCE_HOST="shampad@shampad.ddns.net"
SOURCE_PATH="/var/lib/docker/volumes/deployment_postgres_data/_data/"
TARGET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/db-host"

echo "Starting database sync from ${SOURCE_HOST}:${SOURCE_PATH} → ${TARGET_DIR} ..."

# Create target directory if it doesn't exist
mkdir -p "${TARGET_DIR}"

# rsync flags:
#   -a  archive (preserve perms, times, symlinks, etc.)
#   -v  verbose
#   -z  compress during transfer
#   -P  show progress + resume partial transfers
#   --delete  remove local files that no longer exist on the remote
echo "Syncing contents..."
rsync -avzP --delete "${SOURCE_HOST}:${SOURCE_PATH}" "${TARGET_DIR}/"

# Fix ownership so local postgres container (UID/GID 999) can read the data
echo "Fixing ownership (999:999) for local postgres container..."
sudo chown -R 999:999 "${TARGET_DIR}"

echo "Database sync completed successfully!"
echo "Local db-host directory has been updated from remote."
