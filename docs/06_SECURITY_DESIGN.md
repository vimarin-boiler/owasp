# 6. Diseño de seguridad

## 6.1 Autenticación

- Password hashing Argon2id.
- Política mínima configurable de longitud y complejidad razonable.
- Cambio obligatorio en primer acceso.
- Comparaciones constantes realizadas por la biblioteca de hash.
- Contador de fallos y bloqueo temporal progresivo.
- `session.clear()` antes de `login_user()` para regenerar el contexto de sesión.
- Expiración absoluta e inactividad configurables.
- Registro de login, logout, fallos y bloqueos.

## 6.2 Autorización

Se combinará RBAC con contexto:

- Rol global: admin, respondent o reviewer.
- Membresía activa en organización.
- Asignación explícita al assessment.
- Ownership de respuesta/evidencia.
- Estado actual del assessment y de la pregunta.

Las políticas se implementarán en `permissions.py` y servicios, no solo ocultando botones.

Ejemplo de regla para descargar evidencia:

```text
permitir si:
  usuario activo
  AND pertenece a la organización
  AND (admin OR asignado al assessment)
  AND evidencia pertenece al assessment solicitado
  AND evidencia no está eliminada
```

## 6.3 Prevención de IDOR

- URLs y API usan UUID públicos.
- Cada consulta se restringe por organización y asignación.
- No se aceptan IDs de assessment y evidencia sin verificar la relación entre ambos.
- Se incluyen pruebas cruzadas entre organizaciones y usuarios.

## 6.4 CSRF, XSS y CSP

- Flask-WTF/CSRFProtect para formularios y operaciones mutables.
- API basada en sesión exige token CSRF por encabezado.
- Escape automático Jinja2.
- No se renderiza HTML de comentarios de usuario.
- CSP restrictiva con scripts y estilos locales; nonce solo cuando sea necesario.
- Sin `unsafe-eval`.

## 6.5 Encabezados y cookies

- `Content-Security-Policy`.
- `X-Frame-Options: DENY` o `frame-ancestors 'none'`.
- `X-Content-Type-Options: nosniff`.
- `Referrer-Policy: strict-origin-when-cross-origin`.
- `Permissions-Policy` mínima.
- HSTS solo en producción HTTPS.
- Cookies `HttpOnly`, `SameSite=Lax` y `Secure` en producción.

## 6.6 Archivos

- Storage fuera de `static`.
- Límite de 20 MB configurable y límite de cantidad por pregunta.
- Nombre interno UUID; `secure_filename` solo para nombre de presentación seguro.
- Validación de extensión y MIME detectado por contenido.
- Lista de denegación adicional para ejecutables y scripts.
- Rechazo de archivos con nombre vacío, NUL, traversal o doble extensión peligrosa.
- ZIP no se extrae durante carga; se inspeccionan límites y firmas para mitigar zip bombs.
- Hash SHA-256 y bloqueo de sobrescritura.
- Cuarentena y adaptador ClamAV.
- Descarga forzada, sin ejecución inline por defecto.

## 6.7 Base de datos

- ORM y parámetros enlazados.
- Foreign keys activas en SQLite.
- WAL y timeout de escritura.
- Transacciones explícitas en importación, revisión y publicación.
- Restricciones únicas y checks para estados/ponderaciones.
- Sin SQL específico de SQLite en lógica de negocio.

## 6.8 Auditoría

- Eventos estructurados, append-only.
- Valores antes/después sanitizados.
- No registrar password, session cookie, tokens o bytes de archivos.
- Correlation ID por request.
- Auditoría dentro de la misma transacción cuando la acción cambia datos.
- Logs de aplicación separados de la bitácora funcional.

## 6.9 Rate limiting

Límites diferenciados para:

- Login y recuperación de contraseña.
- Carga/descarga de evidencias.
- API.
- Generación de reportes.
- Importación y restore.

En despliegues de una sola instancia puede usarse memoria; en producción escalada se migrará a Redis.
