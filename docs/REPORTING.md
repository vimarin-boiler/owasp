# Subsistema de reportes

## Principio de consistencia

`ReportDataService` construye un payload neutral que alimenta:

- `reports/printable.html`.
- `ReportExcelService`.
- `ReportPdfService`.

Así, todos los formatos utilizan la misma fuente, dimensiones, recomendaciones y trazabilidad.

## Política de snapshot

- Administrador y revisor asignado: pueden generar una vista previa del cálculo vigente.
- Respondedor: requiere resultados publicados y usa exclusivamente el snapshot publicado.
- La fuente de scoring se conserva en el payload.
- El hash de entrada y la versión de fórmula se muestran en los entregables.

## Vista web imprimible

Contiene:

- Portada.
- Resumen ejecutivo.
- Funciones y prácticas.
- Matriz de brechas.
- Recomendaciones y roadmap.
- Evidencias.
- Preguntas observadas.
- Historial de revisiones y auditoría.

La hoja `app/static/css/report-print.css` define tamaño A4, saltos de página y eliminación de controles al imprimir.

## Excel

Hojas generadas:

1. Resumen ejecutivo.
2. Funciones.
3. Prácticas.
4. Flujos.
5. Preguntas.
6. Evidencias.
7. Recomendaciones.
8. Roadmap.
9. Revisiones.
10. Historial respuestas.
11. Bitácora.

Las hojas incluyen filtros, encabezados fijos, tablas y ajuste de columnas. Las brechas usan formato condicional.

## PDF

El PDF usa ReportLab y contiene:

- Portada corporativa sin logotipos protegidos.
- Tabla de contenidos y bookmarks.
- Radar vectorial por función.
- Barras vectoriales por práctica.
- Tablas repetibles con encabezado.
- Recomendaciones, roadmap y anexos.
- Metadata de documento.
- Pie de página y clasificación.

Las evidencias binarias no se incrustan. Se listan nombre, tipo, tamaño, validación y SHA-256.

La identidad del encabezado y la clasificación se configuran con `REPORT_COMPANY_NAME` y `REPORT_CLASSIFICATION`. `REPORT_LOGO_PATH` permite incorporar un archivo PNG o JPEG autorizado en la portada PDF; cuando no se configura, el documento utiliza una portada tipográfica sin logotipo.

## Seguridad

- Requiere sesión autenticada.
- Aplica `can_view_results`.
- Previene acceso entre organizaciones.
- Rate limit de 10 XLSX y 6 PDF por minuto por identidad remota.
- `Cache-Control: no-store, private`.
- `X-Content-Type-Options: nosniff`.
- CSP `sandbox` en PDF.
- Nombres de descarga saneados con `secure_filename`.
- Generación auditada.

## Extensión futura

El payload puede alimentar un servicio asíncrono, almacenamiento de objetos o plantillas adicionales sin modificar el motor de scoring.
