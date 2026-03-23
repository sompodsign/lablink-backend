#!/usr/bin/env bash
# Complete backup script: backup Lablink database and upload to GCS
# This is the main entry point called by cron

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the project root directory (parent of backup_utility/)
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load environment variables from lablink-backup.env file
# This includes backup settings, GCS configuration, etc.
if [[ -f "${SCRIPT_DIR}/lablink-backup.env" ]]; then
  set -a  # Export all variables
  source "${SCRIPT_DIR}/lablink-backup.env"
  set +a  # Stop exporting
fi

# Enable strict error handling:
# -e: Exit on any error
# -u: Exit on undefined variable
# -o pipefail: Exit on pipe failures
set -euo pipefail

# Run the main backup script which will:
# 1. Create compressed archive of database data
# 2. Upload to GCS
# 3. Clean up old backups
"${SCRIPT_DIR}/db-backup.sh"
