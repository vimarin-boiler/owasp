# Despliegue con Docker

## Preparación

```bash
cp .env.example .env
```

Configure al menos:

```env
FLASK_ENV=production
SECRET_KEY=<valor aleatorio de 32 o más caracteres>
SESSION_COOKIE_SECURE=false
FORCE_HTTPS=false
TRUSTED_HOSTS=localhost,127.0.0.1
CREATE_DEMO_DATA=false
```

Para TLS real, ubique un reverse proxy externo y active cookies seguras y HTTPS.

## Construcción y ejecución

```bash
docker compose build --pull
docker compose up -d
docker compose ps
docker compose logs -f app
```

Acceso local: `http://localhost:8080`.

## Inicialización

El entrypoint aplica migraciones. Para crear el administrador y cargar SAMM:

```bash
docker compose exec app flask seed
```

No habilite `RUN_SEED_ON_START=true` de forma permanente.

## Volúmenes

- `samm_instance`: SQLite y archivos de instancia.
- `samm_uploads`: evidencias.
- `samm_backups`: respaldos.
- `samm_reports`: reservado para futuras persistencias de reportes.

## Backup

```bash
docker compose exec app flask backup
```

Copiar un respaldo al host:

```bash
docker compose cp app:/app/backups/samm-backup-YYYYMMDDTHHMMSSZ.zip ./
```

## Restore

Copie el ZIP dentro del contenedor y detenga el tráfico:

```bash
docker compose cp ./backup.zip app:/app/backups/restore.zip
docker compose stop nginx
docker compose exec app flask restore --file /app/backups/restore.zip --yes
docker compose restart app
docker compose start nginx
```

## Controles de seguridad

- Usuario no root.
- `no-new-privileges`.
- Capabilities eliminadas.
- `/tmp` como tmpfs.
- Nginx de solo lectura.
- App no publica el puerto directamente.
- Healthchecks para app y dependencia de Nginx.

## Actualización

```bash
docker compose exec app flask backup
docker compose build --pull
docker compose up -d --remove-orphans
```

Revise logs y healthcheck después de la actualización.
