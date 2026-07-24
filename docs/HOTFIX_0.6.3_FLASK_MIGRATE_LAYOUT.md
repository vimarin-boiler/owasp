# Hotfix 0.6.3: ubicación de `alembic.ini`

## Problema

`flask db upgrade` buscaba `migrations/alembic.ini`, pero el archivo estaba en la raíz del proyecto. Esto producía:

```text
FileNotFoundError: migrations\\alembic.ini doesn't exist
```

## Corrección

- `alembic.ini` fue movido a `migrations/alembic.ini`.
- `script_location` ahora utiliza `%(here)s`.
- `prepend_sys_path` apunta a `%(here)s/..` para cargar la aplicación desde la raíz.
- Se agregó `tests/test_migration_layout.py` como prueba de regresión.

## Ejecución

Desde la raíz del proyecto:

```powershell
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py run --debug
```
