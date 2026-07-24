#!/bin/sh
set -eu

APP_DIR=${APP_DIR:-/opt/samm-assessment}
APP_USER=${APP_USER:-samm}
APP_GROUP=${APP_GROUP:-samm}

if [ "$(id -u)" -ne 0 ]; then
  echo "Este script debe ejecutarse como root." >&2
  exit 1
fi

getent group "$APP_GROUP" >/dev/null 2>&1 || groupadd --system "$APP_GROUP"
id "$APP_USER" >/dev/null 2>&1 || useradd --system --gid "$APP_GROUP" --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR" /etc/samm-assessment /var/log/samm-assessment
cp -a . "$APP_DIR"/
python3.12 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
mkdir -p "$APP_DIR/instance" "$APP_DIR/uploads" "$APP_DIR/backups" "$APP_DIR/reports"
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR" /var/log/samm-assessment
chmod 0750 "$APP_DIR" "$APP_DIR/instance" "$APP_DIR/uploads" "$APP_DIR/backups" "$APP_DIR/reports" /var/log/samm-assessment
install -m 0644 "$APP_DIR/deploy/systemd/samm-assessment.service" /etc/systemd/system/samm-assessment.service
install -m 0644 "$APP_DIR/deploy/systemd/samm-assessment-backup.service" /etc/systemd/system/samm-assessment-backup.service
install -m 0644 "$APP_DIR/deploy/systemd/samm-assessment-backup.timer" /etc/systemd/system/samm-assessment-backup.timer
install -m 0644 "$APP_DIR/deploy/logrotate/samm-assessment" /etc/logrotate.d/samm-assessment
systemctl daemon-reload
echo "Instalación base completada. Configura /etc/samm-assessment/samm-assessment.env antes de iniciar el servicio."
