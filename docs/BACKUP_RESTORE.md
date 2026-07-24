# Backup y restauración

## Alcance

Los comandos integrados están diseñados para SQLite. En PostgreSQL deben reemplazarse por herramientas nativas como `pg_dump`, `pg_restore` y snapshots del almacenamiento de evidencias.

## Crear un respaldo

```bash
flask --app run.py backup
```

Con ruta explícita:

```bash
flask --app run.py backup --output /srv/backups/samm-manual.zip
```

La base se copia con `sqlite3.Connection.backup`, lo que genera una imagen consistente aun cuando SQLite está en WAL. Luego se ejecuta `PRAGMA integrity_check`.

## Contenido

```text
metadata.json
manifest.json
database/samm_assessment.db
evidences/<assessment_uuid>/<question_uuid>/<file_uuid.ext>
```

`manifest.json` registra SHA-256 y tamaño de cada archivo. La cuarentena no se incluye.

## Validar y restaurar

```bash
flask --app run.py restore --file /srv/backups/samm-manual.zip
```

Automatizado:

```bash
flask --app run.py restore --file /srv/backups/samm-manual.zip --yes
```

Por defecto se crea un respaldo previo. Solo debe usarse `--no-safety-backup` cuando exista una copia externa verificada.

## Controles de restauración

- Cantidad máxima de entradas.
- Límite de tamaño descomprimido.
- Rechazo de rutas absolutas y `..`.
- Rechazo de enlaces simbólicos.
- Rechazo de relación de compresión anómala.
- Presencia de componentes obligatorios.
- Verificación SHA-256 y tamaño.
- Rechazo de archivos no declarados en el manifiesto.
- Compatibilidad del formato.
- `PRAGMA integrity_check`.
- Reemplazo por staging.
- Eliminación de WAL y SHM previos.

## Procedimiento productivo recomendado

1. Habilitar ventana de mantenimiento.
2. Detener Nginx o retirar la instancia del balanceador.
3. Detener Gunicorn: `sudo systemctl stop samm-assessment`.
4. Crear un respaldo adicional.
5. Ejecutar restore.
6. Ejecutar `flask db upgrade`.
7. Iniciar Gunicorn.
8. Verificar `/api/v1/health`.
9. Validar acceso y evidencias.
10. Reincorporar la instancia al tráfico.

## Retención

La entrega incluye un timer diario a las 02:30 y `deploy/scripts/prune-backups.sh`. Se recomienda:

- 7 respaldos diarios.
- 4 semanales.
- 12 mensuales.
- Copia fuera del servidor.
- Cifrado del repositorio de respaldos.
- Prueba de restauración trimestral.
