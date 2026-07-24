# Reporte de validación — Fase 2

Fecha: 24 de julio de 2026.

## Validaciones ejecutadas

| Validación | Resultado |
|---|---:|
| Compilación AST/bytecode de Python | Correcta |
| Parsing de 18 plantillas Jinja2 | Correcto |
| Configuración de mappers SQLAlchemy | Correcta |
| Registro de tablas en metadata | 29 tablas |
| Creación directa de metadata en SQLite | Correcta |
| Migración Alembic `upgrade` en SQLite | Correcta, 29 tablas |
| Migración Alembic `downgrade` en SQLite | Correcta, 0 tablas |
| Diferencias entre migración y metadata SQLAlchemy | 0 diferencias |
| Referencias de iconos SVG | 16 referencias, 0 faltantes |
| Dependencias frontend remotas | Ninguna |
| Archivos de fuentes incluidos | Ninguno |

## Suite pytest incluida

La entrega contiene pruebas para:

- Política de contraseñas.
- Login correcto e incorrecto.
- Bloqueo de cuentas.
- Cambio obligatorio de contraseña.
- Logout por POST.
- Encabezados de seguridad.
- RBAC.
- Prevención de acceso administrativo por respondedores.
- Búsqueda por UUID y comportamiento ante IDs desconocidos.
- Creación y duplicidad de usuarios.
- Protección de la cuenta administrativa propia.
- Slugs organizacionales únicos.
- Redacción de datos sensibles en auditoría.
- Integridad del modelo de 29 tablas.
- Upgrade y downgrade de la migración inicial.

## Restricción del entorno de construcción

El entorno utilizado para empaquetar esta entrega no permitió resolver paquetes externos desde PyPI. Por ello se ejecutaron validaciones estáticas, de SQLAlchemy y de Alembic con las bibliotecas disponibles, pero la suite HTTP completa debe ejecutarse después de instalar `requirements-dev.txt` en el entorno objetivo.
