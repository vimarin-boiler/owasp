# Fase 2 — Entrega técnica

## Objetivo

Entregar una base Flask ejecutable, modular y segura sobre la cual implementar el catálogo SAMM y los assessments sin reestructurar el núcleo de la aplicación.

## Componentes entregados

| Componente | Estado | Implementación |
|---|---:|---|
| Application factory | Completo | `app/__init__.py` |
| Configuración por entorno | Completo | `config.py` |
| Extensiones Flask | Completo | `app/extensions.py` |
| Modelo SQLAlchemy | Completo | `app/models/` |
| Migración inicial | Completo | `migrations/versions/0001_initial.py` |
| Autenticación | Completo | `app/auth/` |
| RBAC | Completo | `app/common/permissions.py` |
| Administración de usuarios | Completo | `app/admin/` |
| Administración de organizaciones | Completo | `app/admin/` |
| Auditoría | Completo | `app/services/audit_service.py` |
| Layout Bootstrap 5 | Completo | `app/templates/base.html` |
| Dashboard base | Completo | `app/dashboard/` |
| API versionada | Base completa | `app/api/v1/` |
| Pruebas | Incluidas | `tests/` |

## Decisiones aplicadas desde la Fase 1

- Monolito modular con blueprints.
- Repositorios para centralizar consultas.
- Servicios para reglas y transacciones.
- UUID público separado de la PK interna.
- Catálogo versionado mediante `Question` y `QuestionRevision`.
- Snapshot inmutable en `AssessmentQuestion`.
- Auditoría transversal.
- Evidencias fuera de `static`.
- Tipos portables entre SQLite y PostgreSQL.

## Cambio de diseño validado

`Question` almacena `current_revision_number` en lugar de una clave foránea a `QuestionRevision`. Esta decisión elimina una dependencia circular de DDL entre ambas tablas, simplifica la migración inicial y mantiene la portabilidad SQLite/PostgreSQL. La revisión vigente se resuelve sobre la colección versionada y será controlada por el servicio de publicación de la Fase 3.

## Rutas disponibles

| Método | Ruta | Acceso |
|---|---|---|
| GET/POST | `/auth/login` | Público, limitado por tasa |
| POST | `/auth/logout` | Autenticado |
| GET/POST | `/auth/change-password` | Autenticado |
| GET | `/` | Autenticado |
| GET | `/admin/users` | Administrador |
| GET/POST | `/admin/users/new` | Administrador |
| GET/POST | `/admin/users/<uuid>/edit` | Administrador |
| GET/POST | `/admin/users/<uuid>/reset-password` | Administrador |
| GET | `/admin/organizations` | Administrador |
| GET/POST | `/admin/organizations/new` | Administrador |
| GET/POST | `/admin/organizations/<uuid>/edit` | Administrador |
| GET | `/admin/audit` | Administrador |
| GET | `/api/v1/health` | Público |

## Criterios de aceptación de la Fase 2

- La aplicación posee un punto de entrada WSGI.
- La configuración crítica falla de forma segura cuando falta `SECRET_KEY`.
- La base se crea mediante Alembic.
- Los roles se inicializan con CLI.
- El administrador puede autenticarse.
- El cambio inicial de contraseña es obligatorio.
- El administrador puede crear y editar usuarios.
- El administrador puede asignar roles.
- El administrador puede crear y editar organizaciones.
- Un respondedor no puede acceder a rutas administrativas.
- Todas las rutas administrativas usan UUID públicos.
- Las operaciones principales generan auditoría.
- El layout es responsive y no depende de CDN.
