# Despliegue en Linux

## Arquitectura recomendada

```text
Internet / red corporativa
          |
       TLS 443
          v
        Nginx
          |
   127.0.0.1:8000
          v
       Gunicorn
          |
      Flask / SQLite
          |
 instance + uploads + backups
```

## 1. Prerrequisitos

Ejemplo Ubuntu Server:

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv nginx ca-certificates
```

Cree un volumen con espacio suficiente y respaldo externo.

## 2. Instalación

Desde el directorio del proyecto:

```bash
sudo ./deploy/scripts/install-linux.sh
```

El script instala en `/opt/samm-assessment`, crea el usuario de servicio `samm`, el entorno virtual, carpetas y unidades systemd.

## 3. Variables de entorno

```bash
sudo install -m 0640 -o root -g samm .env.example /etc/samm-assessment/samm-assessment.env
sudo editor /etc/samm-assessment/samm-assessment.env
```

Configuración mínima de producción:

```env
FLASK_ENV=production
SECRET_KEY=<secreto de alta entropía>
DATABASE_URL=sqlite:////opt/samm-assessment/instance/samm_assessment.db
UPLOAD_FOLDER=/opt/samm-assessment/uploads
BACKUP_FOLDER=/opt/samm-assessment/backups
REPORT_FOLDER=/opt/samm-assessment/reports
CATALOG_IMPORT_FOLDER=/opt/samm-assessment/instance/catalog_imports
SESSION_COOKIE_SECURE=true
FORCE_HTTPS=true
TRUST_PROXY_HEADERS=true
TRUSTED_HOSTS=assessment.example.com
CREATE_DEMO_DATA=false
GUNICORN_BIND=127.0.0.1:8000
GUNICORN_WORKERS=3
GUNICORN_THREADS=2
GUNICORN_FORWARDED_ALLOW_IPS=127.0.0.1
```

## 4. Inicialización

```bash
sudo -u samm -H sh -c 'cd /opt/samm-assessment && .venv/bin/flask db upgrade'
sudo -u samm -H sh -c 'cd /opt/samm-assessment && .venv/bin/flask seed'
```

## 5. Nginx y TLS

Edite dominio y rutas de certificados en `deploy/nginx/samm-assessment.conf`.

Para una CA interna:

1. Genere la clave privada en el servidor.
2. Genere un CSR con el FQDN y SAN requerido.
3. Envíe el CSR a la CA corporativa.
4. Instale certificado, cadena y CA.
5. Proteja la clave con modo `0600` y propietario root.
6. Valide con `sudo nginx -t`.

Instalación:

```bash
sudo install -m 0644 deploy/nginx/samm-assessment.conf /etc/nginx/sites-available/samm-assessment
sudo ln -s /etc/nginx/sites-available/samm-assessment /etc/nginx/sites-enabled/samm-assessment
sudo nginx -t
sudo systemctl reload nginx
```

## 6. Servicio

```bash
sudo systemctl enable --now samm-assessment
sudo systemctl status samm-assessment
curl -fsS http://127.0.0.1:8000/api/v1/health
```

## 7. Backup diario

```bash
sudo systemctl enable --now samm-assessment-backup.timer
systemctl list-timers samm-assessment-backup.timer
```

## 8. Permisos

```bash
sudo chown -R samm:samm /opt/samm-assessment/instance /opt/samm-assessment/uploads /opt/samm-assessment/backups /opt/samm-assessment/reports
sudo chmod 0750 /opt/samm-assessment/instance /opt/samm-assessment/uploads /opt/samm-assessment/backups /opt/samm-assessment/reports
sudo chmod 0640 /etc/samm-assessment/samm-assessment.env
```

No otorgue permisos de escritura al usuario de Nginx sobre evidencias o base de datos.

## 9. Logs

```bash
sudo journalctl -u samm-assessment -f
sudo tail -f /var/log/samm-assessment/application.log
```

La configuración logrotate mantiene 30 rotaciones diarias comprimidas.

## 10. Actualización

```bash
sudo systemctl stop samm-assessment
sudo -u samm -H sh -c 'cd /opt/samm-assessment && .venv/bin/flask backup'
# Desplegar código nuevo
sudo -u samm -H sh -c 'cd /opt/samm-assessment && .venv/bin/pip install -r requirements.txt'
sudo -u samm -H sh -c 'cd /opt/samm-assessment && .venv/bin/flask db upgrade'
sudo systemctl start samm-assessment
curl -fsS https://assessment.example.com/api/v1/health
```

## 11. Respaldo externo

Sincronice los ZIP a un repositorio cifrado fuera del servidor. El backup local no protege contra pérdida total del host.
