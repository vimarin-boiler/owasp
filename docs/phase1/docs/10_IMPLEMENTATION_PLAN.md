# 10. Plan de implementación incremental

## Fase 2 — Proyecto base

Entregables:

- Repositorio ejecutable.
- Application factory, configuración y extensiones.
- Modelos base y primera migración.
- Usuarios, roles y organizaciones.
- Login, logout, cambio inicial de contraseña y bloqueo.
- Layout Bootstrap 5 NTT.
- Fixtures y pruebas iniciales.

Criterio de salida: administrador puede iniciar sesión y administrar usuarios/organizaciones de forma segura.

## Fase 3 — Catálogo SAMM

Entregables:

- Parser `openpyxl`.
- Preview de importación.
- CLI `flask import-samm`.
- CRUD de jerarquía, answer sets y preguntas.
- Versiones draft/published/archived.
- Exportación de catálogo.
- Pruebas de idempotencia y rollback.

Criterio de salida: Excel importado en una versión publicada sin duplicados.

## Fase 4 — Assessment

Entregables:

- Creación y configuración.
- Asignaciones respondent/reviewer.
- Materialización de preguntas.
- Navegación, filtros, autosave y estados.
- Evidencias seguras.
- Revisión, observaciones, rechazo y aprobación.
- Auditoría completa.

Criterio de salida: flujo end-to-end desde respuesta hasta aprobación.

## Fase 5 — Resultados

Entregables:

- Motor de scoring versionado.
- Dashboards por rol.
- Radar, barras, progreso, distribución y brechas.
- Recomendaciones y roadmap.
- Snapshots de resultados.

Criterio de salida: score reproducible y consistente con fixtures derivados del Excel.

## Fase 6 — Reportes y despliegue

Entregables:

- Reportes web, Excel y PDF.
- API v1 y OpenAPI.
- Backup y restore.
- Docker y healthcheck.
- Gunicorn, Nginx y systemd.
- README operativo y hardening.

Criterio de salida: despliegue reproducible y pruebas principales exitosas.
