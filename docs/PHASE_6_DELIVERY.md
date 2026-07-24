# Fase 6 - Reportes y despliegue

## Alcance entregado

La Fase 6 completa la plataforma con entregables ejecutivos y componentes operativos de producción.

### Reportes

- Centro de reportes por assessment.
- Vista web imprimible y responsive.
- Exportación Excel con once hojas especializadas.
- PDF corporativo generado con ReportLab.
- Portada, tabla de contenidos, gráficos, resultados, brechas, recomendaciones y roadmap.
- Identidad, clasificación y logotipo autorizado configurables mediante variables de entorno.
- Anexos de evidencias, observaciones, revisiones y auditoría.
- Descargas privadas y registro en auditoría.
- Uso obligatorio del snapshot publicado para respondedores.

### Backup y restauración

- `flask backup`.
- `flask restore --file ...`.
- Copia consistente de SQLite.
- Inclusión de evidencias y exclusión de cuarentena.
- Metadata del respaldo y versión de aplicación.
- Manifiesto SHA-256.
- Validación contra traversal, symlinks y bombas ZIP.
- `PRAGMA integrity_check` antes de restaurar.
- Respaldo de seguridad previo por defecto.

### Contenedores

- Dockerfile multiuso con Python 3.12 slim.
- Usuario no root.
- Healthcheck.
- Migraciones automáticas configurables.
- Docker Compose con volúmenes persistentes.
- Nginx de reverse proxy para ejecución local.
- Controles `no-new-privileges` y reducción de capacidades.

### Producción Linux

- Configuración Gunicorn.
- Nginx con TLS y headers.
- Servicio systemd endurecido.
- Servicio y timer de backup.
- Logrotate.
- Script de instalación base.
- Guías de permisos, certificados, respaldos y operación.

## Archivos incorporados

```text
app/reports/
app/services/report_data_service.py
app/services/report_excel_service.py
app/services/report_pdf_service.py
app/services/backup_service.py
app/static/css/report-print.css
app/static/js/report-print.js
Dockerfile
docker-compose.yml
docker/entrypoint.sh
docker/nginx.conf
gunicorn.conf.py
deploy/nginx/samm-assessment.conf
deploy/systemd/*.service
deploy/systemd/*.timer
deploy/logrotate/samm-assessment
deploy/scripts/*.sh
tests/test_phase6_reports.py
tests/test_phase6_backup.py
```

## Decisiones técnicas

1. Los tres formatos usan un payload común para evitar diferencias entre resultados.
2. Los PDFs se generan programáticamente, sin dependencias de navegador ni LibreOffice.
3. El Excel usa `openpyxl`, estilos, tablas, filtros y formato condicional.
4. Los archivos se generan en memoria y no permanecen en un directorio público.
5. Los respondedores no pueden generar reportes de cálculos no publicados.
6. Backup y restore se limitan explícitamente a SQLite.
7. La restauración se diseña para ejecutarse en una ventana de mantenimiento.
8. No se agregó una migración porque la auditoría existente cubre la generación de reportes.

## Criterios de aceptación cubiertos

- Reporte ejecutivo web.
- Exportación Excel.
- PDF corporativo.
- Recomendaciones y roadmap incluidos.
- Historial y bitácora incluidos.
- Backup y restore.
- Docker y persistencia.
- Gunicorn, Nginx y systemd.
- TLS, permisos y logrotate documentados.
- Pruebas automatizadas de reportes y respaldos incluidas.
