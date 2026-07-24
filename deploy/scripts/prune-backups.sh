#!/bin/sh
set -eu
BACKUP_DIR=${BACKUP_DIR:-/opt/samm-assessment/backups}
RETENTION_DAYS=${RETENTION_DAYS:-30}
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'samm-backup-*.zip' -mtime "+$RETENTION_DAYS" -print -delete
