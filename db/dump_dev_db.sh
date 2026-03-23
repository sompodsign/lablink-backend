#!/usr/bin/env bash
# Copy the live production PostgreSQL data directory into a separate dev_db directory.
# Both directories live inside the same Docker volume base on the production server.
#
# Usage (run on the production server, or via ssh):
#   bash dump_dev_db.sh
#
# The dev_db copy can then be mounted as a separate postgres container for
# staging / development work without touching the live data.

set -euo pipefail

SOURCE_DIR="/var/lib/docker/volumes/deployment_postgres_data/_data"
TARGET_DIR="/var/lib/docker/volumes/deployment_postgres_dev_data/_data"

echo "Starting database copy: ${SOURCE_DIR} → ${TARGET_DIR}"

# Validate source
if [[ ! -d "${SOURCE_DIR}" ]]; then
    echo "Error: Source directory ${SOURCE_DIR} does not exist" >&2
    exit 1
fi

# Ensure target volume directory exists
if [[ ! -d "${TARGET_DIR}" ]]; then
    echo "Target directory ${TARGET_DIR} does not exist — creating it..."
    sudo mkdir -p "${TARGET_DIR}"
fi

# Wipe target contents so we get a clean copy
echo "Clearing ${TARGET_DIR} ..."
sudo rm -rf "${TARGET_DIR:?}"/*

# Copy production data → dev
echo "Copying ${SOURCE_DIR} → ${TARGET_DIR} ..."
sudo cp -a "${SOURCE_DIR}/." "${TARGET_DIR}/"

# Set correct ownership for the PostgreSQL process inside Docker (UID/GID 999)
echo "Setting PostgreSQL ownership (999:999)..."
sudo chown -R 999:999 "${TARGET_DIR}"

echo "Done! dev_db directory has been refreshed from production data."
