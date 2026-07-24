# Changelog

## 0.4.0 — 2026-07-24

### Agregado

- Gestión completa de organizaciones y assessments vinculados a una versión publicada del cuestionario.
- Snapshot inmutable de preguntas, criterios, alternativas, ponderaciones y jerarquía al crear un assessment.
- Asignación independiente de respondedores y revisores, con responsables principales.
- Cuestionario navegable por función, práctica, flujo y estado, con búsqueda de texto y progreso por sección.
- Guardado manual, borrador y autosave configurable de respuestas.
- Flujo de envío, aprobación, observación, rechazo y reapertura con historial versionado.
- Observaciones generales del assessment y notificaciones internas.
- Carga múltiple, descarga autorizada, eliminación controlada y validación de evidencias.
- Cola de revisión para administradores y revisores.
- Endpoints API v1 para assessments, preguntas, respuestas y metadatos de evidencias.
- Especificación OpenAPI de la API interna.
- Migración `0003_assessment_workflow`.
- Datos demo opcionales para respondedor, revisor y assessment inicial.

### Seguridad

- Verificación de ownership y asignación en todas las rutas del assessment.
- Nombres internos UUID y almacenamiento privado fuera de `static`.
- Inspección de firmas, MIME efectivo y estructura de archivos Office/ZIP.
- Rechazo de ejecutables, scripts, traversal, enlaces simbólicos y bombas ZIP.
- Hash SHA-256, prevención de duplicados y cuarentena previa a la publicación del archivo.
- Encabezados de descarga segura y auditoría de carga, descarga, eliminación y revisión.
- `CREATE_DEMO_DATA` deshabilitado por defecto; el entorno de ejemplo debe habilitarlo explícitamente.


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
