# Hotfix 0.6.4: argumentos duplicados de Alembic

## Síntoma

`flask --app run.py db upgrade` fallaba con:

```text
TypeError: alembic.context.configure() got multiple values for keyword argument 'compare_type'
```

## Causa

`app/extensions.py` configura Flask-Migrate con `compare_type=True` y
`render_as_batch=True`. Flask-Migrate incorpora ambos valores en
`current_app.extensions["migrate"].configure_args`. El archivo
`migrations/env.py` volvía a enviarlos explícitamente y luego expandía
`**configuration`, duplicando las palabras clave.

## Corrección

El modo online de Alembic ahora pasa una sola fuente de configuración:

```python
configuration = dict(current_app.extensions["migrate"].configure_args)
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    **configuration,
)
```

No se modificaron las revisiones existentes.
