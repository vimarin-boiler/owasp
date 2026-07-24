# NTT DevSecOps Assessment — Fase 2

Base ejecutable y segura para una plataforma de assessments de madurez DevSecOps basada en OWASP SAMM.

Esta entrega implementa la **Fase 2: Proyecto base** definida en la especificación funcional: estructura modular Flask, configuración por entornos, modelo SQLAlchemy completo, migración inicial, autenticación, roles, administración inicial y layout Bootstrap 5.

## Capacidades incluidas

- Application factory y blueprints Flask.
- Configuración separada para desarrollo, pruebas y producción.
- Modelo relacional de 29 tablas preparado para SQLite y PostgreSQL.
- Migración inicial Flask-Migrate/Alembic con `upgrade` y `downgrade`.
- Autenticación con Flask-Login y contraseñas Argon2.
- Regeneración de sesión después del login y del cambio de contraseña.
- Bloqueo temporal tras intentos fallidos configurables.
- Cambio obligatorio de contraseña inicial.
- RBAC con roles `admin`, `respondent` y `reviewer`.
- CRUD inicial de usuarios y organizaciones.
- Restablecimiento administrativo de contraseña.
- UUID públicos en rutas para no exponer IDs secuenciales.
- Auditoría de login, logout, usuarios, roles y organizaciones.
- Protección CSRF y validación de formularios con Flask-WTF.
- CSP, HSTS en producción, anti-clickjacking y protección MIME sniffing.
- Rate limiting para el endpoint de login.
- Bootstrap 5 e iconos SVG servidos localmente, sin CDN ni fuentes externas.
- API versionada con healthcheck en `/api/v1/health`.
- Suite pytest para autenticación, autorización, servicios, modelos, migración e IDOR.

## Alcance de esta fase

Esta fase deja implementadas las entidades que utilizarán las siguientes etapas, pero aún no incorpora:

- Importación del cuestionario SAMM desde Excel: **Fase 3**.
- CRUD del catálogo, revisión y publicación de versiones: **Fase 3**.
- Creación y ejecución de assessments, respuestas y evidencias: **Fase 4**.
- Motor de scoring, dashboards SAMM y recomendaciones: **Fase 5**.
- Reportes PDF/Excel y despliegue productivo completo: **Fase 6**.

No existen funciones simuladas para esos módulos. Los modelos y contratos de persistencia están preparados, mientras las rutas de negocio se incorporarán en su fase correspondiente.

## Requisitos

- Python 3.12 o superior.
- SQLite 3 para desarrollo.
- Sistema operativo Windows, Linux o macOS.

## Estructura principal

```text
samm_assessment/
├── app/
│   ├── admin/                 # Gestión inicial de usuarios y organizaciones
│   ├── api/v1/                # API versionada
│   ├── auth/                  # Login, logout y cambio de contraseña
│   ├── common/                # Seguridad, validación y utilidades
│   ├── dashboard/             # Dashboard base por rol
│   ├── models/                # 29 tablas SQLAlchemy
│   ├── repositories/          # Acceso a datos
│   ├── services/              # Casos de uso y reglas de negocio
│   ├── static/                # CSS, JS, Bootstrap e iconos locales
│   └── templates/             # Jinja2 y layout corporativo
├── migrations/                # Alembic / Flask-Migrate
├── scripts/                   # Utilidades de inicialización
├── tests/                     # Pruebas automatizadas
├── uploads/                   # Evidencias privadas, fuera de static
├── config.py
├── run.py
├── wsgi.py
├── requirements.txt
└── .env.example
```

## Instalación en Linux o macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python scripts/generate_secret.py
```

Copia el valor generado en `SECRET_KEY` dentro de `.env`. Cambia también `INITIAL_ADMIN_PASSWORD`.

```bash
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py run
```

La aplicación quedará disponible en:

```text
http://127.0.0.1:5000
```

## Instalación en Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python .\scripts\generate_secret.py
```

Copia el valor generado en `SECRET_KEY` dentro de `.env`. Cambia también `INITIAL_ADMIN_PASSWORD`.

```powershell
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py run
```

## Variables críticas

```env
SECRET_KEY=<valor-aleatorio-de-al-menos-32-caracteres>
DATABASE_URL=sqlite:///instance/samm_assessment.db
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=<contraseña-temporal-segura>
SESSION_COOKIE_SECURE=false
FORCE_HTTPS=false
```

En producción debes habilitar:

```env
FLASK_ENV=production
SESSION_COOKIE_SECURE=true
FORCE_HTTPS=true
TRUST_PROXY_HEADERS=true
```

`TRUST_PROXY_HEADERS=true` presupone que la aplicación está detrás de un reverse proxy controlado. No expongas Gunicorn directamente a redes no confiables con esta opción activa.

## Migraciones

Aplicar todas las migraciones:

```bash
flask --app run.py db upgrade
```

Revisar la versión actual:

```bash
flask --app run.py db current
```

Crear una migración después de modificar modelos:

```bash
flask --app run.py db migrate -m "descripcion del cambio"
```

La migración generada debe revisarse antes de ejecutar `upgrade`.

## Datos iniciales

El comando siguiente es idempotente:

```bash
flask --app run.py seed
```

Crea:

- Roles administrador, respondedor y revisor.
- Administrador configurado mediante variables de entorno.
- Organización de demostración.

La cuenta inicial queda marcada para cambio obligatorio de contraseña.

También puedes crear un administrador interactivo:

```bash
flask --app run.py create-admin
```

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

Con cobertura:

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html
```

Verificación rápida:

```bash
python scripts/smoke_check.py
```

## API base

```http
GET /api/v1/health
```

Respuesta:

```json
{
  "application": "NTT DevSecOps Assessment",
  "status": "ok",
  "version": "0.2.0"
}
```

Los endpoints funcionales indicados en la especificación serán incorporados incrementalmente sin romper el prefijo `/api/v1/`.

## Seguridad implementada

### Identidad y sesión

- Argon2 mediante `argon2-cffi`.
- Política mínima configurable.
- Mensajes de login no enumerables.
- Verificación de hash ficticio para usuarios inexistentes.
- Bloqueo temporal configurable.
- Session protection fuerte.
- Sesión regenerada después de autenticar.
- Timeout por inactividad y timeout absoluto.
- Cookies `HttpOnly`, `SameSite` y `Secure` en producción.
- Logout únicamente mediante POST protegido por CSRF.

### Autorización

- Decoradores de roles aplicados en servidor.
- Carga exclusiva de usuarios activos.
- UUID públicos para navegación.
- Verificación de recursos por UUID y respuesta 404 para recursos inexistentes.
- Protección para impedir que el administrador desactive su propia cuenta o se quite su rol.

### Aplicación web

- CSRF global.
- Escape automático Jinja2.
- ORM SQLAlchemy, sin SQL concatenado.
- Content Security Policy sin `unsafe-inline`.
- Recursos frontend locales.
- `X-Frame-Options: DENY`.
- `X-Content-Type-Options: nosniff`.
- `Referrer-Policy` y `Permissions-Policy`.
- HSTS al operar por HTTPS en producción.
- Correlation ID por solicitud.
- Páginas de error sin stack trace.

### Auditoría

Se registran actor, acción, entidad, UUID público, fecha, IP, User-Agent, valores anteriores y posteriores, resultado y correlation ID. Las claves sensibles son redactadas antes de persistirse.

## Base de datos y portabilidad

- Los modelos utilizan SQLAlchemy 2.x y tipos portables.
- Los enums se almacenan como texto validado en lugar de enums nativos del motor.
- Los cambios de esquema se gestionan con Alembic.
- SQLite activa claves foráneas, WAL y `busy_timeout`.
- No se usa SQL específico de SQLite en la lógica funcional.
- La futura migración a PostgreSQL requiere cambiar `DATABASE_URL`, instalar el driver y ejecutar las migraciones en una base vacía.

Ejemplo futuro:

```env
DATABASE_URL=postgresql+psycopg://user:password@database:5432/samm_assessment
```

## Recursos visuales

Bootstrap y el subconjunto de Bootstrap Icons se incluyen localmente en `app/static/vendor`. No se incluyen logotipos corporativos protegidos ni archivos de fuentes. El logotipo autorizado podrá agregarse posteriormente en `app/static/img`.

## Documentos de la entrega

- `docs/PHASE_2_DELIVERY.md`
- `docs/SECURITY_BASELINE.md`
- `docs/DATA_MODEL_PHASE2.md`
- `docs/VALIDATION_REPORT.md`

## Credenciales de demostración

No se fijan credenciales dentro del código. Los valores se obtienen desde `.env` y el usuario inicial debe cambiar su contraseña en el primer acceso.

## Próxima fase

La Fase 3 incorporará el parser de `SAMM_spreadsheet.xlsx`, previsualización transaccional, catálogo jerárquico, criterios de calidad, respuestas ponderadas y versionamiento publicable del cuestionario.
