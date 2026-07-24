## 0.6.5 - Hotfix creación de assessments

- Evita la doble asociación de cada `AssessmentQuestion` a `Assessment.questions`.
- Construye los snapshots bajo `db.session.no_autoflush` antes de mutar la colección ORM.
- Precarga `QuestionRevision.question` al recuperar una versión de cuestionario.
- Agrega pruebas de regresión para el snapshot sin asociación y la carga eager del catálogo.

## 0.6.1 - Hotfix CSRF

- Corrige `WTF_CSRF_TIME_LIMIT` para usar segundos enteros compatibles con ItsDangerous.
- Agrega `WTF_CSRF_TIME_LIMIT_SECONDS` a `.env.example`.
- Agrega una prueba de regresión para el tipo del límite CSRF.

# Changelog

## 0.6.0 - Fase 6

- Centro de reportes por assessment.
- Vista web imprimible.
- Exportación Excel multipestaña.
- Reporte PDF corporativo con tabla de contenidos y gráficos vectoriales.
- Auditoría y autorización de reportes.
- API de enlaces de reportes.
- Backup y restore con SHA-256 e integridad SQLite.
- Dockerfile, Docker Compose y entrypoint.
- Gunicorn, Nginx, systemd, timer de backup y logrotate.
- Documentación final de instalación, producción y seguridad.
- Pruebas automatizadas para reportes y respaldos.

## 0.5.0 - Fase 5

- Motor de scoring 0-3.
- Snapshots reproducibles.
- Dashboards, brechas, recomendaciones y roadmap.

## 0.4.0 - Fase 4

- Ejecución de assessments, respuestas, evidencias y revisión.

## 0.3.0 - Fase 3

- Catálogo SAMM, importación Excel y versionamiento.

## 0.2.0 - Fase 2

- Proyecto base, autenticación, RBAC y administración.
