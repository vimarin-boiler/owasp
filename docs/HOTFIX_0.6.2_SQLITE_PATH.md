# Hotfix 0.6.2: ruta SQLite

## Problema

La configuración `DATABASE_URL=sqlite:///instance/samm_assessment.db` es relativa.
Flask-SQLAlchemy 3 resuelve las rutas SQLite relativas desde `app.instance_path`,
por lo que la ubicación terminaba siendo `instance/instance/samm_assessment.db`.
SQLite fallaba con `unable to open database file` cuando la carpeta anidada no existía.

## Corrección

- `config.resolve_database_url()` convierte rutas SQLite relativas en rutas absolutas.
- La fábrica Flask crea el directorio padre de la base antes de inicializar el ORM.
- `.env.example` usa la forma portátil `sqlite:///samm_assessment.db`.
- Se agregaron pruebas de regresión para SQLite y PostgreSQL.

## Actualización manual

En `.env` use:

```env
DATABASE_URL=sqlite:///samm_assessment.db
```

Luego ejecute:

```powershell
New-Item -ItemType Directory -Force .\instance | Out-Null
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py run --debug
```
