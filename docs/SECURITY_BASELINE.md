# Línea base de seguridad — Fase 5

## Autenticación

- Argon2 para almacenamiento de contraseñas.
- Hash ficticio ante correos inexistentes para reducir diferencias temporales observables.
- Mensaje genérico para credenciales inválidas.
- Bloqueo temporal después del umbral configurado.
- Rehash automático cuando cambian los parámetros de Argon2.
- Cambio obligatorio de contraseña temporal.

## Sesiones

- `HttpOnly` habilitado.
- `SameSite=Lax` por defecto.
- `Secure` obligatorio en producción.
- Limpieza de sesión antes de autenticar.
- Protección fuerte de Flask-Login.
- Timeout de inactividad y timeout absoluto.
- Logout por POST con CSRF.

## Autorización

La autorización se aplica en servidor y no depende del menú. Se validan:

1. Sesión y usuario activo.
2. Rol requerido.
3. Organización cuando corresponda.
4. Asignación al assessment.
5. Ownership de respuesta o evidencia.
6. Estado de publicación para resultados.

Los IDs internos no aparecen en rutas. Los UUID públicos reducen enumeración, pero no reemplazan las comprobaciones contextuales.

## Resultados

- Administradores y revisores autorizados pueden previsualizar resultados.
- Los respondedores requieren un assessment publicado o cerrado y una fecha de publicación.
- La publicación identifica un único snapshot vigente.
- El hash SHA-256 registra las entradas relevantes del cálculo.
- Reabrir el assessment vuelve a ocultar resultados al respondedor.
- La API aplica las mismas reglas que la interfaz web.

## Evidencias

- Almacenamiento privado fuera de `static`.
- Nombres y directorios internos con UUID.
- Cuarentena previa al almacenamiento definitivo.
- Firma y estructura verificadas.
- Límites de tamaño, cantidad, elementos y expansión.
- Rechazo de ejecutables, scripts, traversal y enlaces simbólicos.
- Hash SHA-256 y prevención de duplicados.
- Descarga autorizada con `no-store`, `nosniff` y CSP `sandbox`.
- Contrato preparado para integración antivirus.

El scanner nulo solo es apropiado para desarrollo. Producción debe conectar un scanner real.

## Seguridad HTTP

Encabezados globales:

- `Content-Security-Policy`.
- `X-Content-Type-Options`.
- `X-Frame-Options`.
- `Referrer-Policy`.
- `Permissions-Policy`.
- `Strict-Transport-Security` cuando HTTPS está forzado.

La CSP:

- Restringe por defecto al mismo origen.
- Impide `object`, framing y bases externas.
- Permite scripts propios y la distribución fijada de Chart.js en `cdn.jsdelivr.net`.
- Permite estilos solo desde el mismo origen.
- Permite atributos `style` necesarios para porcentajes y medidores dinámicos mediante `style-src-attr 'unsafe-inline'`.
- Bloquea fuentes externas.
- Limita conexiones al mismo origen.

Para eliminar `style-src-attr 'unsafe-inline'` será necesario reemplazar los porcentajes dinámicos por clases predefinidas o propiedades aplicadas desde un script con nonce.

## Chart.js

La URL está fijada y se configura con `CHART_JS_URL`. Una ruta estática local funciona sin ampliar la CSP. Un dominio externo diferente requiere actualizar explícitamente la política antes del despliegue.

## Auditoría

Los datos se sanitizan antes de persistir. Claves asociadas a contraseñas, tokens, secretos y CSRF se reemplazan por `[REDACTED]`.

La bitácora registra actor, acción, entidad, organización, assessment, IP, User-Agent, valores anteriores y nuevos, resultado, error y correlation ID.

## Reverse proxy

`ProxyFix` solo debe habilitarse detrás de un proxy controlado que reemplace y sanee `X-Forwarded-For`, `X-Forwarded-Proto` y `Host`. La aplicación confía en un único salto.

## Producción

- `SECRET_KEY` aleatoria y externa al repositorio.
- `SESSION_COOKIE_SECURE=true`.
- `FORCE_HTTPS=true`.
- `CREATE_DEMO_DATA=false`.
- PostgreSQL para concurrencia sostenida.
- Scanner antivirus real.
- TLS y headers revisados en Nginx.
- Logs centralizados con control de acceso y rotación.
- Backups cifrados y probados.
