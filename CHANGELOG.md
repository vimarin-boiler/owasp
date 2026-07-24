# Changelog

## 0.3.0 — 2026-07-24

### Agregado

- Importador seguro y transaccional de `SAMM_spreadsheet.xlsx`.
- Vista previa persistente con errores y advertencias por hoja, fila y campo.
- Comando `flask import-samm` con modo `--dry-run` y publicación opcional.
- Administración de funciones, prácticas, flujos y niveles de madurez.
- Administración de conjuntos de respuesta y ponderaciones.
- Preguntas con revisiones inmutables, criterios de calidad y duplicación.
- Versiones de cuestionario en estado borrador, publicada o archivada.
- Exportación de versiones a un workbook compatible con la importación.
- API autenticada para preguntas y versiones del cuestionario.
- Migración `0002_catalog_imports` y bitácora de importaciones.
- Pruebas de importación, versionamiento, exportación y autorización.

### Seguridad

- Inspección del contenedor XLSX antes de procesarlo.
- Límites de entradas, tamaño descomprimido y relación de compresión.
- Nombres internos aleatorios y almacenamiento temporal privado.
- Hash SHA-256 de archivos y contenido versionado.
- Mensajes internos sanitizados y registro técnico en logs.

## 0.2.0 — 2026-07-24

### Agregado

- Proyecto Flask modular.
- Configuración development/testing/production.
- Modelo SQLAlchemy de 29 tablas.
- Migración Alembic inicial.
- Autenticación y gestión segura de sesión.
- Roles administrador, respondedor y revisor.
- Administración de usuarios y organizaciones.
- Auditoría de seguridad.
- Layout Bootstrap 5 inspirado en NTT DATA.
- API `/api/v1/health`.
- Pruebas automatizadas de la Fase 2.
