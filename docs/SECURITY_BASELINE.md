# Línea base de seguridad — Fase 2

## Autenticación

- Argon2 para almacenamiento de contraseñas.
- Hash ficticio ante correos inexistentes para reducir diferencias de tiempo observables.
- Mensaje genérico para credenciales inválidas.
- Bloqueo temporal después del umbral configurado.
- Rehash automático cuando cambian los parámetros recomendados de Argon2.
- Cambio obligatorio de contraseña temporal.

## Sesiones

- `HttpOnly` siempre habilitado.
- `SameSite=Lax` por defecto.
- `Secure` obligatorio en producción.
- Regeneración lógica de sesión mediante `session.clear()` antes de `login_user`.
- Protección fuerte de Flask-Login.
- Timeout de inactividad y timeout absoluto.
- Logout por POST con CSRF.

## Autorización

La autorización se aplica en la vista y no depende del estado visual del menú. El decorador `roles_required` verifica:

1. Sesión autenticada.
2. Usuario activo.
3. Presencia de al menos uno de los roles requeridos.

Los IDs internos no aparecen en las rutas. Los recursos se consultan por UUID público y las búsquedas inexistentes retornan 404.

## Seguridad HTTP

Encabezados aplicados globalmente:

- `Content-Security-Policy`
- `X-Content-Type-Options`
- `X-Frame-Options`
- `Referrer-Policy`
- `Permissions-Policy`
- `Strict-Transport-Security` cuando la solicitud es HTTPS y `FORCE_HTTPS` está activo.

La CSP permite scripts, estilos, imágenes y conexiones exclusivamente desde el mismo origen, salvo imágenes `data:`. No se permite contenido embebido ni `unsafe-inline`.

## Auditoría

Los datos se sanitizan antes de persistir. Las claves asociadas a contraseñas, tokens, secretos y CSRF se reemplazan por `[REDACTED]`.

La bitácora registra:

- Actor.
- Acción.
- Entidad y UUID público.
- Organización y assessment cuando corresponda.
- IP de origen.
- User-Agent.
- Antes y después.
- Resultado y código de error.
- Correlation ID.

## Reverse proxy

`ProxyFix` solo debe habilitarse cuando Nginx u otro proxy controlado reemplaza y sanea `X-Forwarded-For`, `X-Forwarded-Proto` y `Host`. La aplicación confía en un único salto de proxy.

## Pendientes por fase

- Validación MIME profunda y cuarentena: Fase 4.
- Integración antivirus: interfaz en Fase 4.
- Permisos por asignación de assessment: Fase 4.
- Firma o protección adicional de reportes: Fase 6.
