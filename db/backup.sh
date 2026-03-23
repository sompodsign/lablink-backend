#!/usr/bin/env bash
# Convenience wrapper: runs the full backup + GCS upload pipeline
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/backup_utility/run-backup-and-upload-to-gcs.sh"
