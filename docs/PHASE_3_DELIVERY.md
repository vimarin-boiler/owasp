# Fase 3 — Catálogo OWASP SAMM

## Objetivo

Esta fase convierte la base de la Fase 2 en un administrador funcional del catálogo OWASP SAMM. La solución importa el archivo Excel oficial entregado, conserva la jerarquía del modelo, administra alternativas ponderadas y crea versiones inmutables del cuestionario.

## Capacidades implementadas

### Importación Excel

- Lectura con `openpyxl` de `imp-questions`, `imp-answers` y metadatos de versión.
- Verificación previa del contenedor XLSX para mitigar archivos comprimidos maliciosos.
- Validación de encabezados, campos obligatorios, identificadores, niveles, conjuntos de respuesta y ponderaciones.
- Vista previa persistente antes de confirmar.
- Errores y advertencias asociados a hoja, fila y campo.
- Hash SHA-256 del archivo y hashes de contenido para respuestas y preguntas.
- Aplicación transaccional: un error revierte todos los cambios del catálogo.
- Reimportación idempotente: las preguntas y conjuntos sin cambios se reutilizan.
- Carga web privada y eliminación del archivo temporal tras confirmar.
- Comando CLI con modo de solo validación.

### Catálogo jerárquico

- CRUD de funciones de negocio.
- CRUD de prácticas de seguridad.
- CRUD de flujos o subcategorías.
- CRUD de niveles de madurez.
- Desactivación lógica en elementos maestros.
- Restricción de cambios estructurales cuando un maestro ya forma parte de revisiones históricas.

### Respuestas y preguntas

- Administración de conjuntos de respuesta con cuatro alternativas ponderadas.
- Protección de conjuntos ya utilizados por revisiones.
- Alta de preguntas manuales.
- Creación automática de una revisión nueva al editar.
- Historial de revisiones con motivo del cambio y hash de contenido.
- Duplicación controlada de preguntas.
- Criterios de calidad independientes y ordenados.

### Versionamiento

- Creación de versiones desde las revisiones vigentes.
- Clonación de la composición de una versión anterior.
- Publicación y archivado.
- Archivado automático de la versión publicada anterior.
- Publicación de las revisiones vinculadas.
- Exportación de una versión a un Excel compatible con las hojas de importación.

### Integraciones

- `flask seed` importa y publica el catálogo configurado si la base aún no contiene versiones.
- API autenticada para preguntas y versiones bajo `/api/v1/`.
- Dashboard administrativo con métricas del catálogo.
- Auditoría de vistas previas, confirmaciones, maestros, preguntas y versiones.

## Resultado del archivo fuente

| Métrica | Resultado |
|---|---:|
| Funciones de negocio | 5 |
| Prácticas de seguridad | 15 |
| Flujos | 30 |
| Niveles de madurez | 3 |
| Preguntas | 90 |
| Conjuntos de respuesta | 24 |
| Criterios de calidad | 295 |
| Errores | 0 |
| Advertencias | 0 |

## Archivos principales incorporados

```text
app/catalog/
app/services/samm_workbook_parser.py
app/services/samm_import_service.py
app/services/catalog_service.py
app/services/questionnaire_service.py
app/services/catalog_export_service.py
migrations/versions/0002_catalog_imports.py
data/SAMM_spreadsheet.xlsx
tests/test_samm_workbook_parser.py
tests/test_catalog_import_service.py
tests/test_catalog_versioning.py
tests/test_catalog_export.py
tests/test_catalog_routes.py
```

## Fuera del alcance de esta fase

- Creación y asignación de assessments.
- Respuestas y evidencias por assessment.
- Revisión y aprobación de respuestas.
- Cálculo de resultados, brechas y recomendaciones.
- Reportes ejecutivos PDF.

Esas capacidades corresponden a las fases 4, 5 y 6.
