# Hotfix 6.1: error de validación CSRF

## Síntoma

Al enviar un formulario, la aplicación podía fallar con:

```text
TypeError: '>' not supported between instances of 'int' and 'datetime.timedelta'
```

## Causa

`WTF_CSRF_TIME_LIMIT` estaba configurado con `timedelta(hours=2)`. Flask-WTF pasa este valor a ItsDangerous como `max_age`, cuyo contrato requiere segundos enteros o `None`.

## Corrección

```python
WTF_CSRF_TIME_LIMIT = env_int("WTF_CSRF_TIME_LIMIT_SECONDS", 7200)
```

Y en `.env`:

```env
WTF_CSRF_TIME_LIMIT_SECONDS=7200
```

Después de aplicar el cambio, reinicie el servidor y recargue la página del formulario para generar un token CSRF nuevo.
