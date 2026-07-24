#!/bin/sh
set -eu

mkdir -p "${UPLOAD_FOLDER:-/app/uploads}" "${BACKUP_FOLDER:-/app/backups}" "${REPORT_FOLDER:-/app/reports}" /app/instance/catalog_imports

if [ "${RUN_MIGRATIONS_ON_START:-true}" = "true" ]; then
  flask db upgrade
fi

if [ "${RUN_SEED_ON_START:-false}" = "true" ]; then
  flask seed
fi

exec "$@"
